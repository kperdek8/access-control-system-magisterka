import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Any, Dict
from exceptions import SchemaMappingNotFoundError, SelfDelegationNotAllowedError, DurationExceededLimitError
import uvicorn
import requests
from fastapi import FastAPI, HTTPException

from common.registry import SchemaRegistry
from delegations import add_delegation, revoke_delegation, get_delegations
from common.schemas import AuthorizationRequest, AuthorizationResponse, Decision, Mode, AttributeResponse, \
    AttributeRequest, Behaviour, AddDelegationResponse, RevokeDelegationResponse, AddDelegationRequest, \
    RevokeDelegationRequest
from common.logger import get_logger, log_evaluation_decision
from common.settings import Settings
from parser import load_and_parse_policies, PolicyStore
from transformer import Rule, DelegationRule
from attributes import get_attributes, get_attributes_batch

logger = get_logger("PDP-SERVICE")
#logger.setLevel("DEBUG")
PIP_URL = os.getenv("PIP_URL")
resource_schema_path = os.getenv("RESOURCE_SCHEMA_PATH")

schema_registry: SchemaRegistry
policies: PolicyStore
behaviour: Behaviour


@asynccontextmanager
async def lifespan(app: FastAPI):
    global policies
    global behaviour
    global schema_registry
    schema_registry = SchemaRegistry(path=resource_schema_path)
    policies = load_and_parse_policies(schema_registry=schema_registry)
    settings_path = os.getenv("SETTINGS_PATH")
    settings = Settings(settings_path)
    behaviour = settings.get_pdp_mode()
    if behaviour not in [Behaviour.PERMIT_OVERRIDE, Behaviour.DENY_OVERRIDE]:
        raise RuntimeError(f"Invalid behaviour in settings file. Please use '{Behaviour.DENY_OVERRIDE}' or '{Behaviour.PERMIT_OVERRIDE}'.")
    else:
        logger.info(f"PDP started with mode: {behaviour}")
    yield

app = FastAPI(lifespan=lifespan)


def evaluate_delegation_request(request: AddDelegationRequest):
    schemas = [request.resource_type, request.delegatee_type, request.delegator_type]
    for schema in schemas:
        if not schema_registry.get_mapping(schema):
            raise SchemaMappingNotFoundError(entity_type=schema)

    if request.delegator_type == request.delegatee_type and request.delegator_id == request.delegatee_id:
            raise SelfDelegationNotAllowedError

    action = request.action[0] if isinstance(request.action, list) else request.action
    applicable_rules = policies.find_delegation(res_type=request.resource_type,
                                                delegatee_type=request.delegatee_type,
                                                delegator_type=request.delegator_type,
                                                action=action)

    resource_primary_key = schema_registry.get_primary_key_for_type(res_type=request.resource_type)
    delegator_primary_key = schema_registry.get_primary_key_for_type(res_type=request.delegator_type)
    delegatee_primary_key = schema_registry.get_primary_key_for_type(res_type=request.delegatee_type)

    attributes = {
        "resource": {resource_primary_key: request.resource_id, "type": request.resource_type},
        "delegator": {delegator_primary_key: request.delegator_id, "type": request.delegator_type},
        "delegatee": {delegatee_primary_key: request.delegatee_id, "type": request.delegatee_type}
    }

    missing_attributes = {
        "resource": set(),
        "delegatee": set(),
        "delegator": set()
    }

    for delegation_rule in applicable_rules:
        for category, attr_name in delegation_rule.rule.collect_attributes():
            if category == "resource" and attr_name not in attributes["resource"]:
                missing_attributes["resource"].add(attr_name)
            elif category == "delegatee" and attr_name not in attributes["delegatee"]:
                missing_attributes["delegatee"].add(attr_name)
            elif category == "delegator" and attr_name not in attributes["delegator"]:
                missing_attributes["delegator"].add(attr_name)

    if missing_attributes["resource"]:
        attributes["resource"].update(get_attributes(pip_url=PIP_URL,
                                                     id=attributes["resource"][resource_primary_key],
                                                     type=attributes["resource"]["type"],
                                                     attributes=missing_attributes["resourcet"]))
    if missing_attributes["delegatee"]:
        attributes["delegatee"].update(get_attributes(pip_url=PIP_URL,
                                                      id=attributes["delegatee"][resource_primary_key],
                                                      type=attributes["delegatee"]["type"],
                                                      attributes=missing_attributes["delegatee"]))
    if missing_attributes["delegator"]:
        attributes["delegator"].update(get_attributes(pip_url=PIP_URL,
                                                      id=attributes["delegator"][resource_primary_key],
                                                      type=attributes["delegator"]["type"],
                                                      attributes=missing_attributes["delegator"]))

    context = {
        "resource": attributes["resource"],
        "delegatee": attributes["delegatee"],
        "delegator": attributes["delegator"],
        "context": {"action": request.action}
    }

    for delegation_rule in applicable_rules:
        if delegation_rule.rule.evaluate(context=context):
            return True
    return False


def evaluate_decision(subject_attributes: dict, resource_attributes: dict, request_context: dict):
    step_times = {
        "1_prepare_request": 0.0,
        "2_fetch_pip_attrs": 0.0,
        "3_evaluate_access_rules": 0.0,
        "4_fetch_delegations": 0.0,
        "5_fetch_delegators_attrs": 0.0,
        "6_evaluate_delegation_rules": 0.0
    }
    decision_reason = "Brak reguł zezwalających"
    final_decision = False  # Domyślnie zakaz

    # Przygotowanie żądania z atrybutami
    start_step1 = time.perf_counter()

    missing_attributes = {
        "subject": set(),
        "resource": set()
    }

    for policy in policies.rules:
        for category, attr_name in policy.collect_attributes():
            if category == "subject" and attr_name not in subject_attributes:
                missing_attributes["subject"].add(attr_name)
            elif category == "resource" and attr_name not in resource_attributes:
                missing_attributes["resource"].add(attr_name)

    step_times["1_prepare_request"] = time.perf_counter() - start_step1

    # Otrzymanie atrybutów z PIP
    start_step2 = time.perf_counter()

    if missing_attributes["subject"]:
        subject_attributes.update(get_attributes(pip_url=PIP_URL,
                                                 id=subject_attributes["id"],
                                                 type=subject_attributes["type"],
                                                 attributes=missing_attributes["subject"]))
    if missing_attributes["resource"]:
        resource_attributes.update(get_attributes(pip_url=PIP_URL,
                                                  id=resource_attributes["id"],
                                                  type=resource_attributes["type"],
                                                  attributes=missing_attributes["resource"]))

    step_times["2_fetch_pip_attrs"] = time.perf_counter() - start_step2

    # Ewaluacja reguł dostępowych
    start_step3 = time.perf_counter()

    context = {
        "subject": subject_attributes,
        "resource": resource_attributes,
        "context": request_context
    }

    access_evaluated = False
    for policy in policies.rules:
        decision = policy.evaluate(context)
        if decision == "ALLOW" and behaviour == Behaviour.PERMIT_OVERRIDE:
            final_decision = True
            decision_reason = f"Reguła ALLOW: {policy.conditions}"
            access_evaluated = True
            break
        elif decision == "ALLOW":
            final_decision = True
            decision_reason = f"Reguła ALLOW: {policy.conditions}"
        elif decision == "DENY" and behaviour == Behaviour.DENY_OVERRIDE:
            final_decision = False
            decision_reason = f"Reguła DENY: {policy.conditions}"
            access_evaluated = True
            break

    step_times["3_evaluate_access_rules"] = time.perf_counter() - start_step3

    # Jeśli podjęto ostateczną decyzję na etapie reguł dostępu (Permit/Deny Override), pomijamy delegacje
    if access_evaluated:
        log_evaluation_decision(logger, final_decision, decision_reason, step_times)
        return final_decision

    applicable_delegation_rules = policies.find_delegation_by_delegatee(res_type=resource_attributes["type"],
                                                                        delegatee_type=subject_attributes["type"],
                                                                        action=request_context["action"])
    if not final_decision and applicable_delegation_rules:
        # Pobranie dostępnych delegacji
        start_step4 = time.perf_counter()

        delegations = get_delegations(pip_url=PIP_URL,
                                      subject_id=subject_attributes["id"],
                                      subject_type=subject_attributes["type"],
                                      resource_id=resource_attributes["id"],
                                      resource_type=resource_attributes["type"])
        step_times["4_fetch_delegations"] = time.perf_counter() - start_step4

        if delegations:
            # Pobranie atrybutów delegatorów
            start_step5 = time.perf_counter()

            logger.debug(f"Found {len(delegations)} active delegations in PIP.")
            missing_delegators_attrs = defaultdict(set)
            missing_delegation_subject_attrs = set()
            missing_delegation_resource_attrs = set()

            valid_delegation_candidates = []

            for delegation in delegations:
                # 1. Znajdź istotne reguły w PolicyStore na podstawie metadanych wpisu delegacji
                relevant_rules = policies.find_delegation(
                    res_type=delegation.resource_type,
                    delegatee_type=delegation.delegatee_type,
                    delegator_type=delegation.delegator_type,
                    action=request_context["action"]
                )

                # 2. Jeżeli dana delegacja nie posiada istotnej reguły w PolicyStore, uznaj ją za nieważną
                if not relevant_rules:
                    continue

                valid_delegation_candidates.append({
                    "delegation": delegation,
                    "rules": relevant_rules
                })

                # 3. Zbierz wymagane atrybuty
                for d_rule in relevant_rules:
                    for category, attribute in d_rule.rule.collect_attributes():
                        if category == "delegator":
                            delegator_key = (delegation.delegator_type, delegation.delegator_id)
                            missing_delegators_attrs[delegator_key].add(attribute)
                        elif category == "delegatee" and attribute not in subject_attributes:
                            missing_delegation_subject_attrs.add(attribute)
                        elif category == "resource" and attribute not in resource_attributes:
                            missing_delegation_resource_attrs.add(attribute)

            fetched_batch_data = {}
            pip_batch_payload = []

            # A. Dodaj do batcha unikalnych delegatorów
            for (del_type, del_id), attrs in missing_delegators_attrs.items():
                pip_batch_payload.append({
                    "id": del_id,
                    "type": del_type,
                    "attributes": list(attrs)
                })
            # B. Jeśli brakuje atrybutów podmiotu (delegatee dla wpisu delegacji), dodaj go do tego samego batcha
            if missing_delegation_subject_attrs:
                pip_batch_payload.append({
                    "id": str(subject_attributes["id"]),
                    "type": subject_attributes["type"],
                    "attributes": list(missing_delegation_subject_attrs)
                })
            # C. Jeśli brakuje atrybutów zasobu, dodaj go do tego samego batcha
            if missing_delegation_resource_attrs:
                pip_batch_payload.append({
                    "id": str(resource_attributes["id"]),
                    "type": resource_attributes["type"],
                    "attributes": list(missing_delegation_resource_attrs)
                })

            if pip_batch_payload:
                fetched_batch_data = get_attributes_batch(pip_url=PIP_URL, entities_to_fetch=pip_batch_payload)

            # 4. Zaktualizuj zasób i podmiot o brakujące atrybuty
            if missing_delegation_subject_attrs:
                extra_subject_data = fetched_batch_data.get(subject_attributes["type"], {}).get(str(subject_attributes["id"]), {})
                subject_attributes.update(extra_subject_data)

            if missing_delegation_resource_attrs:
                extra_resource_data = fetched_batch_data.get(resource_attributes["type"], {}).get(str(resource_attributes["id"]), {})
                resource_attributes.update(extra_resource_data)

            step_times["5_fetch_delegators_attrs"] = time.perf_counter() - start_step5

            # 5. Ewaluacja reguł delegacji z kompletnym kontekstem
            start_step6 = time.perf_counter()
            delegation_approved = False

            for candidate in valid_delegation_candidates:
                current_delegation = candidate["delegation"]
                current_rules = candidate["rules"]

                del_type = current_delegation.delegator_type
                del_id = str(current_delegation.delegator_id)
                delegator_attributes = fetched_batch_data.get(del_type, {}).get(del_id, {})

                delegation_context = {
                    "subject": subject_attributes,
                    "resource": resource_attributes,
                    "delegator": delegator_attributes,
                    "context": request_context
                }

                final_rule = None
                for d_rule in current_rules:
                    try:
                        if d_rule.rule.evaluate(delegation_context):
                            if current_delegation.duration <= d_rule.max_duration:
                                delegation_approved = True
                                final_rule = d_rule
                                break
                            else:
                                logger.warning(f"Delegation rejected: duration limit exceeded.")
                    except Exception as e:
                        logger.error(f"Error during continuous verification evaluation: {e}")
                        continue

                if delegation_approved:
                    final_decision = True
                    logger.debug(f"Access granted based on delegation: {current_delegation} fulfilling rule: {final_rule.rule}")
                    decision_reason = f"Zezwolenie na podstawie aktywnej delegacji (Reguła: {getattr(final_rule.rule, 'text', str(final_rule.rule))})"
                    break
            step_times["6_evaluate_delegation_rules"] = time.perf_counter() - start_step6
    log_evaluation_decision(logger, final_decision, decision_reason, step_times)
    return final_decision


def evaluate_constraints(subject_attributes: dict, resource_attributes: dict, context: dict):
    missing_attributes = {
        "subject": set()
    }

    for policy in policies.rules:
        for category, attr_name in policy.collect_attributes():
            if category == "subject" and attr_name not in subject_attributes:
                missing_attributes["subject"].add(attr_name)

    if missing_attributes["subject"]:
        subject_attributes.update(get_attributes(pip_url=PIP_URL,
                                                 id=subject_attributes["id"],
                                                 type=subject_attributes["type"],
                                                 attributes=missing_attributes["subject"]))

    context = {
        "subject": subject_attributes,
        "resource": resource_attributes,
        "context": context
    }

    all_applicable_constraints = []
    any_allow = False

    for policy in policies.rules:
        action, constraints = policy.collect_constraints(context)

        if action == "ALLOW":
            any_allow = True
            if constraints is None:
                continue

            if constraints == []:
                return Decision.ALLOW, []

            all_applicable_constraints.extend(constraints)

    if any_allow and all_applicable_constraints:
        return Decision.ALLOW, all_applicable_constraints

    if any_allow:
        return Decision.ALLOW, []

    return Decision.DENY, []


@app.post("/authorize", response_model=AuthorizationResponse)
def authorize(request: AuthorizationRequest) -> AuthorizationResponse:
    logger.debug(f"Received authorization request: {request}")
    context = {
        "action": request.action
    }
    if not request.mode or request.mode == Mode.DECISION:
        if evaluate_decision(request.subject, request.resource, context):
            logger.debug(f"Authorization decision: {Decision.ALLOW}")
            return AuthorizationResponse(decision=Decision.ALLOW)
        else:
            logger.debug(f"Authorization decision: {Decision.DENY}")
            return AuthorizationResponse(decision=Decision.DENY)
    else:
        decision, constraints = evaluate_constraints(request.subject, request.resource, context)
        return AuthorizationResponse(decision=decision, constraints=constraints)


@app.post("/delegations", response_model=AddDelegationResponse)
def add_delegation_endpoint(request: AddDelegationRequest):
    if request.start_date + request.duration < datetime.now():
        raise HTTPException(status_code=400, detail="Delegation already expired.")
    try:
        if evaluate_delegation_request(request=request):
            status_code, result = add_delegation(pip_url=PIP_URL, delegation=request)
            if status_code != 200:
                raise HTTPException(status_code=status_code, detail=result)
            return AddDelegationResponse(detail=result)
        else:
            raise HTTPException(status_code=403, detail="Policy does not allow for this delegation of permissions.")
    except SchemaMappingNotFoundError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SelfDelegationNotAllowedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DurationExceededLimitError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.patch("/delegations/revoke", response_model=RevokeDelegationResponse)
def revoke_delegation_endpoint(request: RevokeDelegationRequest):
    status_code, result = revoke_delegation(pip_url=PIP_URL, delegation=request)

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=result)

    return result


@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_decision_point"}


if __name__ == "__main__":
    # Uruchomienie serwera
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8001
    )