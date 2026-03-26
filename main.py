import os

from services.editor_service import EditorService
from utils.input_handler import (
    choose_from_list,
    choose_scope,
    confirm,
    get_menu_choice,
    get_non_empty_text,
    get_non_negative_int,
    get_positive_int,
)

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
except Exception:
    class _Dummy:
        RED = ''
        GREEN = ''
        YELLOW = ''
        CYAN = ''
        MAGENTA = ''
        WHITE = ''
        RESET_ALL = ''

    Fore = _Dummy()
    Style = _Dummy()


RISK_COLOR = {
    'SAFE': Fore.GREEN,
    'MEDIUM': Fore.YELLOW,
    'DANGEROUS': Fore.RED,
}


def c(text, color):
    return f'{color}{text}{Style.RESET_ALL}'


def get_default_save_path():
    appdata = os.getenv('APPDATA')
    if not appdata:
        return None
    return os.path.join(appdata, 'Balatro\\2\\save.jkr')


def choose_save_path(default_path):
    print(c('Balatro Advanced Save Editor', Fore.CYAN))
    print('----------------------------')

    if default_path:
        print(f'Default save file: {default_path}')
    else:
        print('Default save file: not available (APPDATA is not set)')

    custom_path = input('Enter save file path (leave blank to use default): ').strip()
    if custom_path:
        return custom_path
    return default_path


def safe_get_value(service, keys):
    try:
        return service.get_value(keys)
    except Exception:
        return 'N/A'


def preview_and_confirm(label, current_value, new_value, risk_level, details=None):
    color = RISK_COLOR.get(risk_level, Fore.WHITE)
    print(f'\n{c(label, Fore.MAGENTA)}')
    print(f'Risk: {c(risk_level, color)}')
    if details:
        print(f'Info: {details}')
    print(f'Current value: {current_value}')
    print(f'New value: {new_value}')
    return confirm('Apply this change? (y/n): ')


def apply_scalar_change(label, risk_level, current_value, new_value, apply_fn, details=None):
    if preview_and_confirm(label, current_value, new_value, risk_level, details=details):
        apply_fn(new_value)
        print(c('Applied successfully.', Fore.GREEN))
    else:
        print(c('Canceled.', Fore.YELLOW))


def choose_manual_or_preset(normal_value, high_value, infinite_value):
    while True:
        print('\n1. Manual input')
        print(f'2. Preset Normal ({normal_value})')
        print(f'3. Preset High ({high_value})')
        print(f'4. Preset Infinite ({infinite_value})')
        print('0. Back')
        raw = input('Select an option: ').strip()

        if raw == '0':
            return None
        if raw == '1':
            return get_non_negative_int('Enter value: ')
        if raw == '2':
            return normal_value
        if raw == '3':
            return high_value
        if raw == '4':
            return infinite_value
        print('Invalid option. Please choose a valid menu number.')


def menu_economy_capacity(service):
    while True:
        print(c('\n=== ECONOMY & CAPACITY SYSTEM ===', Fore.CYAN))
        print('1. Edit Money')
        print('2. Edit Interest Cap')
        print('3. Edit Joker Slots')
        print('4. Edit Consumable Slots')
        print('5. Edit Hand Size')
        print('0. Back')
        choice = get_menu_choice({'0', '1', '2', '3', '4', '5'})

        if choice == '0':
            return

        if choice == '1':
            current = safe_get_value(service, ['GAME', 'dollars'])
            value = choose_manual_or_preset(50, 10000, 999999999)
            if value is None:
                continue
            apply_scalar_change('Edit Money', 'SAFE', current, value, service.set_money)

        elif choice == '2':
            current = safe_get_value(service, ['GAME', 'interest_cap'])
            value = choose_manual_or_preset(25, 100, 999999)
            if value is None:
                continue
            apply_scalar_change('Edit Interest Cap', 'MEDIUM', current, value, service.set_interest_cap)

        elif choice == '3':
            current = safe_get_value(service, ['GAME', 'starting_params', 'joker_slots'])
            value = choose_manual_or_preset(5, 20, 999)
            if value is None:
                continue
            apply_scalar_change('Edit Joker Slots', 'MEDIUM', current, value, service.set_joker_slots)

        elif choice == '4':
            current = safe_get_value(service, ['GAME', 'starting_params', 'consumable_slots'])
            value = choose_manual_or_preset(2, 10, 999)
            if value is None:
                continue
            apply_scalar_change('Edit Consumable Slots', 'MEDIUM', current, value, service.set_consumable_slots)

        elif choice == '5':
            current = safe_get_value(service, ['GAME', 'starting_params', 'hand_size'])
            value = choose_manual_or_preset(8, 20, 50)
            if value is None:
                continue
            apply_scalar_change('Edit Hand Size', 'MEDIUM', current, value, service.set_hand_size)


def menu_round_combat(service):
    while True:
        print(c('\n=== ROUND / COMBAT SYSTEM ===', Fore.CYAN))
        print('1. Set Hands Left')
        print('2. Set Discards Left')
        print('3. Set Reroll Cost')
        print('4. Set Blind Requirement')
        print('5. Legacy Auto Chips (target blind - 1)')
        print('0. Back')
        choice = get_menu_choice({'0', '1', '2', '3', '4', '5'})

        if choice == '0':
            return

        if choice in {'1', '2', '3'}:
            print('\n1. Set specific value')
            print('2. Infinite mode')
            print('0. Back')
            sub = get_menu_choice({'0', '1', '2'})
            if sub == '0':
                continue

            if choice == '1':
                current = safe_get_value(service, ['GAME', 'current_round', 'hands_left'])
                value = get_non_negative_int('Enter hands left: ') if sub == '1' else 99
                apply_scalar_change('Set Hands Left', 'SAFE', current, value, service.set_hands_left)

            elif choice == '2':
                current = safe_get_value(service, ['GAME', 'current_round', 'discards_left'])
                value = get_non_negative_int('Enter discards left: ') if sub == '1' else 99
                apply_scalar_change('Set Discards Left', 'SAFE', current, value, service.set_discards_left)

            elif choice == '3':
                current = safe_get_value(service, ['GAME', 'current_round', 'reroll_cost'])
                value = get_non_negative_int('Enter reroll cost: ') if sub == '1' else 0
                apply_scalar_change('Set Reroll Cost', 'MEDIUM', current, value, service.set_reroll_cost)

        elif choice == '4':
            print('\n1. Set specific value')
            print('2. Infinite mode (very high blind)')
            print('3. Instant win (blind = 1)')
            print('0. Back')
            sub = get_menu_choice({'0', '1', '2', '3'})
            if sub == '0':
                continue
            current = safe_get_value(service, ['BLIND', 'chips'])
            if sub == '1':
                value = get_positive_int('Enter blind requirement: ')
            elif sub == '2':
                value = 999999999
            else:
                value = 1
            apply_scalar_change('Set Blind Requirement', 'DANGEROUS', current, value, service.set_blind_requirement)

        elif choice == '5':
            if preview_and_confirm(
                'Legacy Auto Chips',
                safe_get_value(service, ['GAME', 'chips']),
                'Target blind - 1',
                'SAFE',
                details='Uses original logic: set chips to just below current blind target.',
            ):
                service.edit_chips()
                print(c('Applied successfully.', Fore.GREEN))
            else:
                print(c('Canceled.', Fore.YELLOW))


def select_hand_name(service):
    hands = service.get_hand_names()
    if not hands:
        print('No poker hands found.')
        return None
    return choose_from_list('Select poker hand', hands)


def menu_poker_progression(service):
    while True:
        print(c('\n=== POKER HAND PROGRESSION SYSTEM ===', Fore.CYAN))
        print('1. Upgrade specific hand')
        print('2. Set level')
        print('3. Set chips')
        print('4. Set multiplier')
        print('5. Max all hands')
        print('6. Bulk upgrade (selected hands)')
        print('0. Back')
        choice = get_menu_choice({'0', '1', '2', '3', '4', '5', '6'})

        if choice == '0':
            return

        if choice in {'1', '2', '3', '4'}:
            hand = select_hand_name(service)
            if hand is None:
                continue

            if choice == '1':
                stat = choose_from_list('Choose stat to edit', ['level', 'chips', 'mult'])
                if stat is None:
                    continue
            elif choice == '2':
                stat = 'level'
            elif choice == '3':
                stat = 'chips'
            else:
                stat = 'mult'

            current = safe_get_value(service, ['GAME', 'hands', hand, stat])
            value = get_non_negative_int(f'Enter new {stat}: ')
            apply_scalar_change(
                f'Update hand {hand} -> {stat}',
                'MEDIUM',
                current,
                value,
                lambda v, hand_name=hand, stat_name=stat: service.set_hand_stat(hand_name, stat_name, v),
            )

        elif choice == '5':
            if preview_and_confirm(
                'Max All Hands',
                'Current hand progression',
                'level=100, chips=1000000, mult=100000 for all hands',
                'DANGEROUS',
            ):
                count = service.max_all_hands()
                print(c(f'Applied to {count} hands.', Fore.GREEN))
            else:
                print(c('Canceled.', Fore.YELLOW))

        elif choice == '6':
            hands = service.get_hand_names()
            if not hands:
                print('No poker hands found.')
                continue
            print('Available hands:')
            print(', '.join(hands))
            raw = input('Enter hand names separated by comma: ').strip()
            selected = [h.strip() for h in raw.split(',') if h.strip()]
            if not selected:
                print('No valid hand selected.')
                continue

            invalid = [h for h in selected if h not in hands]
            if invalid:
                print(f'Invalid hand names: {", ".join(invalid)}')
                continue

            stat = choose_from_list('Choose stat to edit', ['level', 'chips', 'mult'])
            if stat is None:
                continue
            value = get_non_negative_int(f'Enter new {stat}: ')

            if preview_and_confirm(
                'Bulk Upgrade Selected Hands',
                f'{len(selected)} selected hands',
                f'{stat} = {value}',
                'DANGEROUS',
            ):
                for hand in selected:
                    service.set_hand_stat(hand, stat, value)
                print(c('Bulk update complete.', Fore.GREEN))
            else:
                print(c('Canceled.', Fore.YELLOW))


def select_card_area():
    area = choose_from_list('Select card area', ['jokers', 'deck', 'hand'])
    return area


def resolve_card_scope(service, area_name):
    scope = choose_scope()
    if scope is None:
        return None, None
    if scope == 'all':
        return True, None

    count = service.get_card_count(area_name)
    if count <= 0:
        print('No cards available in this area.')
        return None, None
    idx = get_positive_int(f'Enter card index (1 - {count}): ')
    if idx > count:
        print('Invalid index. Out of range.')
        return None, None
    return False, idx


def menu_deck_card_editor(service):
    while True:
        print(c('\n=== DECK & CARD EDITOR ===', Fore.CYAN))
        print('1. Edit Joker')
        print('2. Edit Deck Card')
        print('3. Edit Hand Card')
        print('0. Back')
        choice = get_menu_choice({'0', '1', '2', '3'})

        if choice == '0':
            return

        area = 'jokers' if choice == '1' else 'deck' if choice == '2' else 'hand'

        while True:
            print(f'\nEditing area: {area}')
            print('1. Change edition')
            print('2. Change seal')
            print('3. Toggle stickers')
            print('0. Back')
            sub = get_menu_choice({'0', '1', '2', '3'})
            if sub == '0':
                break

            apply_all, card_idx = resolve_card_scope(service, area)
            if apply_all is None:
                continue

            if sub == '1':
                edition = choose_from_list('Choose edition', ['foil', 'holographic', 'polychrome', 'negative'])
                if edition is None:
                    continue
                if preview_and_confirm(
                    f'Apply edition: {edition}',
                    'Current edition(s)',
                    f'{edition} on {"all cards" if apply_all else f"card #{card_idx}"}',
                    'MEDIUM',
                ):
                    changed = service.apply_card_edition(area, edition, apply_all=apply_all, card_index=card_idx)
                    print(c(f'Updated cards: {changed}', Fore.GREEN))
                else:
                    print(c('Canceled.', Fore.YELLOW))

            elif sub == '2':
                seal = choose_from_list('Choose seal', ['red', 'blue', 'gold', 'purple'])
                if seal is None:
                    continue
                if preview_and_confirm(
                    f'Apply seal: {seal}',
                    'Current seal(s)',
                    f'{seal} on {"all cards" if apply_all else f"card #{card_idx}"}',
                    'MEDIUM',
                ):
                    changed = service.apply_card_seal(area, seal, apply_all=apply_all, card_index=card_idx)
                    print(c(f'Updated cards: {changed}', Fore.GREEN))
                else:
                    print(c('Canceled.', Fore.YELLOW))

            elif sub == '3':
                sticker = choose_from_list('Choose sticker', ['eternal', 'perishable', 'rental'])
                if sticker is None:
                    continue
                state = choose_from_list('Choose state', ['true', 'false'])
                if state is None:
                    continue
                enabled = state == 'true'
                if preview_and_confirm(
                    f'Toggle sticker: {sticker}',
                    'Current sticker state(s)',
                    f'{sticker}={str(enabled).lower()} on {"all cards" if apply_all else f"card #{card_idx}"}',
                    'DANGEROUS',
                ):
                    changed = service.apply_card_sticker(area, sticker, enabled, apply_all=apply_all, card_index=card_idx)
                    print(c(f'Updated cards: {changed}', Fore.GREEN))
                else:
                    print(c('Canceled.', Fore.YELLOW))


def menu_voucher_metagame(service):
    while True:
        print(c('\n=== VOUCHER & METAGAME SYSTEM ===', Fore.CYAN))
        print('1. Unlock all vouchers')
        print('2. Add specific voucher')
        print('3. Remove voucher')
        print('4. View active vouchers')
        print('0. Back')
        choice = get_menu_choice({'0', '1', '2', '3', '4'})

        if choice == '0':
            return

        if choice == '1':
            if preview_and_confirm('Unlock all vouchers', 'Current voucher state', 'All known vouchers => true', 'MEDIUM'):
                count = service.unlock_all_vouchers()
                print(c(f'Unlocked/updated vouchers: {count}', Fore.GREEN))
            else:
                print(c('Canceled.', Fore.YELLOW))

        elif choice in {'2', '3'}:
            keys = service.list_voucher_keys()
            print('Available voucher keys:')
            print(', '.join(keys))
            voucher_key = get_non_empty_text('Enter voucher key: ')
            enabled = choice == '2'
            current = safe_get_value(service, ['GAME', 'used_vouchers', voucher_key])
            if current == 'N/A':
                print('Voucher key not found in save structure.')
                continue
            if preview_and_confirm(
                f'Update voucher: {voucher_key}',
                current,
                'true' if enabled else 'false',
                'MEDIUM',
            ):
                service.set_voucher(voucher_key, enabled)
                print(c('Voucher updated.', Fore.GREEN))
            else:
                print(c('Canceled.', Fore.YELLOW))

        elif choice == '4':
            active = service.list_active_vouchers()
            print(c(f'Active vouchers ({len(active)}):', Fore.CYAN))
            if active:
                print(', '.join(active))
            else:
                print('(none)')


def menu_rng_probability(service):
    while True:
        print(c('\n=== RNG & PROBABILITY SYSTEM ===', Fore.CYAN))
        print('1. Set base probability denominator')
        print('2. Force 100% RNG success')
        print('3. Edit seed')
        print('4. Custom probability input')
        print('0. Back')
        choice = get_menu_choice({'0', '1', '2', '3', '4'})

        if choice == '0':
            return

        if choice == '1':
            current = safe_get_value(service, ['GAME', 'probabilities', 'normal'])
            value = get_positive_int('Enter denominator (1 means 100%): ')
            apply_scalar_change('Set base probability denominator', 'MEDIUM', current, value, service.set_probability_denominator)

        elif choice == '2':
            current = safe_get_value(service, ['GAME', 'probabilities', 'normal'])
            apply_scalar_change('Force 100% RNG', 'DANGEROUS', current, 1, lambda _v: service.force_100_rng())

        elif choice == '3':
            current = safe_get_value(service, ['GAME', 'pseudorandom', 'seed'])
            seed = get_non_empty_text('Enter new seed: ')
            apply_scalar_change('Edit seed', 'MEDIUM', current, seed, service.set_seed)

        elif choice == '4':
            current = safe_get_value(service, ['GAME', 'probabilities', 'normal'])
            value = get_positive_int('Enter custom denominator: ')
            apply_scalar_change('Custom probability input', 'MEDIUM', current, value, service.set_probability_denominator)


def menu_god_mode(service):
    while True:
        print(c('\n=== GOD MODE / PRESET HACKS ===', Fore.RED))
        print('1. Infinite Everything')
        print('2. Oops! All Negative Jokers')
        print('3. Max All Poker Hands')
        print('4. Free Shop (reroll = 0 forever)')
        print('5. Guaranteed RNG')
        print('6. Unlock Everything')
        print('0. Back')
        choice = get_menu_choice({'0', '1', '2', '3', '4', '5', '6'})

        if choice == '0':
            return

        if choice == '1':
            desc = 'Sets large values for economy/capacity, hands/discards, reroll=0, blind=1, high multipliers.'
            if preview_and_confirm('Infinite Everything', 'Current save state', 'Apply full power preset', 'DANGEROUS', desc):
                service.god_infinite_everything()
                print(c('God mode applied.', Fore.GREEN))

        elif choice == '2':
            desc = 'Attempts to set edition=negative on all joker cards where edition data exists.'
            if preview_and_confirm('Oops! All Negative Jokers', 'Current joker editions', 'negative on all jokers', 'DANGEROUS', desc):
                changed = service.god_all_negative_jokers()
                print(c(f'Updated jokers: {changed}', Fore.GREEN))

        elif choice == '3':
            if preview_and_confirm('Max All Poker Hands', 'Current hand progression', 'Set max level/chips/mult on all hands', 'DANGEROUS'):
                changed = service.god_max_all_hands()
                print(c(f'Updated hands: {changed}', Fore.GREEN))

        elif choice == '4':
            if preview_and_confirm('Free Shop', safe_get_value(service, ['GAME', 'current_round', 'reroll_cost']), 0, 'DANGEROUS'):
                service.god_free_shop()
                print(c('Free Shop applied.', Fore.GREEN))

        elif choice == '5':
            if preview_and_confirm('Guaranteed RNG', safe_get_value(service, ['GAME', 'probabilities', 'normal']), 1, 'DANGEROUS'):
                service.god_guaranteed_rng()
                print(c('Guaranteed RNG applied.', Fore.GREEN))

        elif choice == '6':
            desc = 'Unlocks all vouchers, expands limits, and removes eternal where possible.'
            if preview_and_confirm('Unlock Everything', 'Current unlock state', 'Unlock and expand major systems', 'DANGEROUS', desc):
                service.god_unlock_everything()
                print(c('Unlock Everything applied.', Fore.GREEN))


def menu_search(service):
    print(c('\n=== SEARCH FIELDS ===', Fore.CYAN))
    query = get_non_empty_text('Enter path keyword to search: ')
    results = service.search_fields(query)
    if not results:
        print('No fields found.')
        return
    print(c(f'Found {len(results)} field(s):', Fore.GREEN))
    for path in results:
        print(f'- {path}')


def print_main_menu(service):
    print(c('\n=== BALATRO ADVANCED EDITOR ===', Fore.CYAN))
    print(f'Save file: {service.get_save_file_path()}')
    print(f'Money: {safe_get_value(service, ["GAME", "dollars"])}')
    print(f'Chips: {safe_get_value(service, ["GAME", "chips"])}')
    print('1. Economy & Capacity System')
    print('2. Round / Combat System')
    print('3. Poker Hand Progression System')
    print('4. Deck & Card Editor')
    print('5. Voucher & Metagame System')
    print('6. RNG & Probability System')
    print('7. God Mode / Preset Hacks')
    print('8. Save File')
    print('9. Undo Last Action')
    print('10. Search Fields')
    print('11. Legacy: Edit Multipliers (global)')
    print('12. Legacy: Remove Eternal From Jokers')
    print('13. Legacy: Edit Card Limits')
    print('0. Exit')


def main():
    default_path = get_default_save_path()
    save_path = choose_save_path(default_path)

    if not save_path:
        print('No save file path provided.')
        return

    try:
        service = EditorService(save_path)
    except FileNotFoundError:
        print(f'Error: Save file not found: {save_path}')
        return
    except PermissionError:
        print('Error: Permission denied while opening the save file.')
        return
    except Exception as exc:
        print(f'Error: Could not open or parse save file: {exc}')
        return

    while True:
        print_main_menu(service)
        choice = get_menu_choice({'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13'})

        try:
            if choice == '1':
                menu_economy_capacity(service)
            elif choice == '2':
                menu_round_combat(service)
            elif choice == '3':
                menu_poker_progression(service)
            elif choice == '4':
                menu_deck_card_editor(service)
            elif choice == '5':
                menu_voucher_metagame(service)
            elif choice == '6':
                menu_rng_probability(service)
            elif choice == '7':
                menu_god_mode(service)
            elif choice == '8':
                if confirm('Manual save now? (y/n): '):
                    service.save()
                    print(c('Save file written successfully.', Fore.GREEN))
                else:
                    print(c('Save canceled.', Fore.YELLOW))
            elif choice == '9':
                if service.undo_last_action():
                    print(c('Undo complete. Last action reverted in memory.', Fore.GREEN))
                else:
                    print(c('Nothing to undo.', Fore.YELLOW))
            elif choice == '10':
                menu_search(service)
            elif choice == '11':
                current = 'all hands multipliers'
                value = get_non_negative_int('Enter multiplier value for all hands: ')
                if preview_and_confirm('Legacy Edit Multipliers', current, value, 'MEDIUM'):
                    service.edit_multipliers(value)
                    print(c('Applied successfully.', Fore.GREEN))
            elif choice == '12':
                if preview_and_confirm('Legacy Remove Eternal', 'Current joker sticker state', 'eternal=false on jokers', 'MEDIUM'):
                    service.edit_card_abilities()
                    print(c('Applied successfully.', Fore.GREEN))
            elif choice == '13':
                if preview_and_confirm('Legacy Edit Card Limits', 'Current card limits', 'joker=30, consumable=20', 'MEDIUM'):
                    service.edit_card_limits()
                    print(c('Applied successfully.', Fore.GREEN))
            elif choice == '0':
                print('Exiting.')
                return

        except FileNotFoundError:
            print('Error: Save file path became unavailable.')
        except PermissionError:
            print('Error: Permission denied while updating/writing save file.')
        except ValueError as exc:
            print(f'Input error: {exc}')
        except IndexError as exc:
            print(f'Index error: {exc}')
        except Exception as exc:
            print(f'Unexpected error: {exc}')


if __name__ == '__main__':
    main()
