def get_menu_choice(valid_choices):
    while True:
        raw = input('Select an option: ').strip()
        if raw in valid_choices:
            return raw
        print('Invalid option. Please choose a valid menu number.')


def get_non_empty_text(prompt):
    while True:
        raw = input(prompt).strip()
        if raw:
            return raw
        print('Input cannot be empty.')


def get_non_negative_int(prompt, allow_blank=False, default=None):
    while True:
        raw = input(prompt).strip()
        if allow_blank and raw == '':
            return default

        try:
            value = int(raw)
        except ValueError:
            print('Invalid input. Please enter a whole number.')
            continue

        if value < 0:
            print('Invalid input. Value must be non-negative.')
            continue

        return value


def get_positive_int(prompt, allow_blank=False, default=None):
    while True:
        value = get_non_negative_int(prompt, allow_blank=allow_blank, default=default)
        if value is None:
            return value
        if value <= 0:
            print('Invalid input. Value must be greater than 0.')
            continue
        return value


def choose_from_list(title, options, allow_back=True):
    while True:
        print(f'\n{title}')
        print('-' * len(title))
        for index, option in enumerate(options, start=1):
            print(f'{index}. {option}')
        if allow_back:
            print('0. Back')

        raw = input('Select an option: ').strip()
        if allow_back and raw == '0':
            return None

        try:
            selected = int(raw)
        except ValueError:
            print('Invalid option. Please choose a valid menu number.')
            continue

        if 1 <= selected <= len(options):
            return options[selected - 1]

        print('Invalid option. Please choose a valid menu number.')


def confirm(prompt='Are you sure? (y/n): '):
    while True:
        raw = input(prompt).strip().lower()
        if raw in ('y', 'yes'):
            return True
        if raw in ('n', 'no'):
            return False
        print('Invalid input. Please enter y or n.')


def choose_scope():
    while True:
        print('\nApply scope')
        print('-----------')
        print('1. Single card index')
        print('2. All cards')
        print('0. Back')
        raw = input('Select an option: ').strip()

        if raw == '0':
            return None
        if raw == '1':
            return 'single'
        if raw == '2':
            return 'all'
        print('Invalid option. Please choose a valid menu number.')
