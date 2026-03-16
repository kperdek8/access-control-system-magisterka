def walk_tree(tree):
    path = [tree]  # Stos do przechowywania historii (back)

    while True:
        current_node = path[-1]
        print("\n" + "=" * 40)

        # Sprawdzamy czy to Tree czy Token (liść końcowy)
        if hasattr(current_node, 'data'):
            print(f"AKTUALNY WĘZEŁ: {current_node.data}")
            children = current_node.children
        else:
            print(f"OSIĄGNIĘTO TOKEN: {current_node}")
            children = []

        print("-" * 40)

        # Wyświetlanie dzieci aktualnego węzła
        for i, child in enumerate(children):
            if hasattr(child, 'data'):
                print(f"[{i}] Węzeł: {child.data}")
            else:
                print(f"Token: '{child}' (typ: {child.type})")

        print("\nNawigacja: [cyfra] wejdź | [b] wstecz | [q] wyjdź")
        choice = input("Wybór: ").strip().lower()

        if choice == 'q':
            break
        elif choice == 'b':
            if len(path) > 1:
                path.pop()
            else:
                print("Jesteś na samym szczycie (root).")
        elif choice.isdigit():
            idx = int(choice)
            if 0 <= idx < len(children):
                target = children[idx]
                if hasattr(target, 'data'):
                    path.append(target)
                else:
                    print(f"\n!! Indeks {idx} to Token. Nie można wejść głębiej !!")
            else:
                print("Błędny numer.")
        else:
            print("Nieznana komenda.")