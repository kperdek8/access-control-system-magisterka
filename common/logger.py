import logging
import sys


def get_logger(name: str):
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger


def log_evaluation_decision(logger: logging.Logger, decision: bool, reason: str, metrics: dict):
    """Funkcja pomocnicza generująca czytelny i ustrukturyzowany raport ewaluacji decyzji dostępowej."""
    status = "ALLOWED" if decision else "DENIED"

    log_msg = (
        f"\n[EVALUATION REPORT] Result: {status}\n"
        f"  Reason: {reason}\n"
        f"  Execution breakdown:\n"
        f"    1. Request preparation:           {metrics['1_prepare_request'] * 1000:.4f} ms\n"
        f"    2. PIP attribute fetching:        {metrics['2_fetch_pip_attrs'] * 1000:.4f} ms\n"
        f"    3. Access rule evaluation:        {metrics['3_evaluate_access_rules'] * 1000:.4f} ms\n"
    )

    if metrics['4_fetch_delegations'] > 0:
        log_msg += (
            f"    4. Delegation store fetching:     {metrics['4_fetch_delegations'] * 1000:.4f} ms\n"
            f"    5. Delegator attributes batching: {metrics['5_fetch_delegators_attrs'] * 1000:.4f} ms\n"
            f"    6. Delegation rule evaluation:    {metrics['6_evaluate_delegation_rules'] * 1000:.4f} ms\n"
        )

    total_time = sum(metrics.values()) * 1000
    log_msg += f"  Total processing time: {total_time:.4f} ms"

    logger.info(log_msg)