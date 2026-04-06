import re

from core.balatro_save_file import BalatroSaveFile, MapEntryStruct, MapStruct
from core.token_iterator import TokenIterator


class BalatroSaveEditor(object):
    def __init__(self, save_file_path):
        self.balatro_save_file = BalatroSaveFile(save_file_path)

    def edit_money(self, new_value):
        # Sets the amount of money you have
        self.balatro_save_file['GAME']['dollars'] = str(new_value)

    def edit_hand_size(self, new_size):
        self.balatro_save_file['GAME']['starting_params']['hand_size'] = str(new_size)
        self._set_if_present(['cardAreas', 'hand', 'config', 'card_limit'], new_size)
        self._set_if_present(['cardAreas', 'hand', 'config', 'temp_limit'], new_size)

    def edit_pack_size(self, new_size):
        # Cập nhật giá trị pack_size
        if 'pack_size' not in self.balatro_save_file['GAME']:
            self.balatro_save_file['GAME']['pack_size'] = str(new_size)
        else:
            self.balatro_save_file['GAME']['pack_size'] = str(new_size)

    def edit_joker_max(self, new_max):
        # Cập nhật giới hạn joker theo cấu trúc runtime của game
        if not self._set_if_present(['GAME', 'shop', 'joker_max'], new_max):
            self._set_if_present(['GAME', 'starting_params', 'joker_slots'], new_max)
        self._set_if_present(['cardAreas', 'jokers', 'config', 'card_limit'], new_max)
        self._set_if_present(['cardAreas', 'jokers', 'config', 'temp_limit'], new_max)

    def edit_chips(self):
        # Searches for the current blind's chip target and sets your current chip count to just under it
        try:
            target = int(self.balatro_save_file['BLIND']['chips'].structs[0])
        except ValueError:
            target = int(float(self.balatro_save_file['BLIND']['chips'].structs[0]))
        self.balatro_save_file['GAME']['chips'] = str(target - 1)
        self.balatro_save_file['GAME']['chips_text'] = f'{target - 1:,}'

    def edit_multipliers(self, new_mult=10000):
        # Changes the multiplier for each hand type
        for hand in self.balatro_save_file['GAME']['hands']:
            hand['mult'] = str(new_mult)

    def edit_card_limits(self):
        # Change joker limit
        self.balatro_save_file['cardAreas']['jokers']['config']['card_limit'] = str(30)
        self.balatro_save_file['cardAreas']['jokers']['config']['temp_limit'] = str(30)
        # Change consumable (tarot cards) limit
        self.balatro_save_file['cardAreas']['consumeables']['config']['card_limit'] = str(20)
        self.balatro_save_file['cardAreas']['consumeables']['config']['temp_limit'] = str(20)

    def edit_card_abilities(self):
        # This removes the 'eternal' attribute from all cards in your deck
        for joker in self.balatro_save_file['cardAreas']['jokers']['cards']:
            if 'eternal' in joker['ability']:
                joker['ability']['eternal'] = 'false'

    def _iter_map_entries(self, map_struct):
        for struct in map_struct.structs:
            if hasattr(struct, 'key') and hasattr(struct, 'value'):
                yield struct.key, struct.value

    def _get_by_path(self, keys):
        node = self.balatro_save_file
        for key in keys:
            node = node[key]
        return node

    def _set_by_path(self, keys, value):
        parent = self._get_by_path(keys[:-1])
        parent[keys[-1]] = str(value)

    def _set_if_present(self, keys, value):
        try:
            parent = self._get_by_path(keys[:-1])
        except ValueError:
            return False
        if keys[-1] in parent:
            parent[keys[-1]] = str(value)
            return True
        return False

    def _set_bool_if_exists(self, map_struct, key, value):
        if key in map_struct:
            map_struct[key] = 'true' if value else 'false'
            return True
        return False

    def _parse_literal(self, value):
        text = str(value)
        if text == 'true':
            return True
        if text == 'false':
            return False
        if text == 'nil':
            return None
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
            quote_char = text[0]
            unquoted = text[1:-1]
            unquoted = unquoted.replace('\\' + quote_char, quote_char).replace('\\\\', '\\')
            text = unquoted
        try:
            if '.' in text:
                return float(text)
            return int(text)
        except ValueError:
            return text

    def get_literal_value(self, keys):
        literal = self._get_by_path(keys)
        return str(literal)

    def set_money(self, value):
        self.edit_money(value)

    def set_interest_cap(self, value):
        self._set_by_path(['GAME', 'interest_cap'], value)

    def set_joker_slots(self, value):
        self._set_by_path(['GAME', 'starting_params', 'joker_slots'], value)
        self._set_if_present(['GAME', 'shop', 'joker_max'], value)
        self._set_if_present(['cardAreas', 'jokers', 'config', 'card_limit'], value)
        self._set_if_present(['cardAreas', 'jokers', 'config', 'temp_limit'], value)

    def set_consumable_slots(self, value):
        self._set_by_path(['GAME', 'starting_params', 'consumable_slots'], value)
        self._set_if_present(['cardAreas', 'consumeables', 'config', 'card_limit'], value)
        self._set_if_present(['cardAreas', 'consumeables', 'config', 'temp_limit'], value)

    def set_hand_size(self, value):
        self.edit_hand_size(value)

    def set_hands_left(self, value):
        self._set_by_path(['GAME', 'current_round', 'hands_left'], value)

    def set_discards_left(self, value):
        self._set_by_path(['GAME', 'current_round', 'discards_left'], value)

    def set_reroll_cost(self, value):
        self._set_by_path(['GAME', 'current_round', 'reroll_cost'], value)
        if 'base_reroll_cost' in self.balatro_save_file['GAME']:
            self._set_by_path(['GAME', 'base_reroll_cost'], value)
        if 'round_resets' in self.balatro_save_file['GAME'] and 'reroll_cost' in self.balatro_save_file['GAME']['round_resets']:
            self._set_by_path(['GAME', 'round_resets', 'reroll_cost'], value)

    def set_blind_requirement(self, value):
        self._set_by_path(['BLIND', 'chips'], value)
        if 'chip_text' in self.balatro_save_file['BLIND']:
            self._set_by_path(['BLIND', 'chip_text'], value)

    def get_hand_names(self):
        hands = self.balatro_save_file['GAME']['hands']
        return [key for key, _ in self._iter_map_entries(hands)]

    def set_hand_stat(self, hand_name, stat_name, value):
        hand = self.balatro_save_file['GAME']['hands'][hand_name]
        hand[stat_name] = str(value)

    def max_all_hands(self, level=100, chips=1000000, mult=100000):
        changed = 0
        for _, hand in self._iter_map_entries(self.balatro_save_file['GAME']['hands']):
            if 'level' in hand:
                hand['level'] = str(level)
            if 'chips' in hand:
                hand['chips'] = str(chips)
            if 'mult' in hand:
                hand['mult'] = str(mult)
            changed += 1
        return changed

    def _card_area_cards(self, area_name):
        return self.balatro_save_file['cardAreas'][area_name]['cards']

    def get_card_count(self, area_name):
        cards = self._card_area_cards(area_name)
        count = 0
        for _k, _v in self._iter_map_entries(cards):
            count += 1
        return count

    def _iter_cards(self, area_name):
        cards = self._card_area_cards(area_name)
        for key, card in self._iter_map_entries(cards):
            yield key, card

    def _get_card_by_position(self, area_name, position):
        idx = 1
        for key, card in self._iter_cards(area_name):
            if idx == position:
                return key, card
            idx += 1
        raise IndexError('Card index out of range')

    def _set_edition_on_card(self, card, edition_name):
        if edition_name is None:
            return True

        if str(edition_name).strip() == '':
            if 'edition' in card:
                self._remove_map_key(card, 'edition')
            return True

        edition = self._ensure_child_map(card, 'edition')
        if edition is None:
            return False
        normalized_name = {
            'holographic': 'holo',
            'holo': 'holo',
            'foil': 'foil',
            'polychrome': 'polychrome',
            'negative': 'negative',
        }.get(edition_name, edition_name)

        if normalized_name not in ('foil', 'holo', 'polychrome', 'negative'):
            return False

        for key_name in ('foil', 'holo', 'holographic', 'polychrome', 'negative', 'chips', 'mult', 'x_mult'):
            self._remove_map_key(edition, key_name)

        self._set_raw_lua_value(edition, 'type', self._lua_string_literal(normalized_name))

        if normalized_name == 'foil':
            self._set_raw_lua_value(edition, 'foil', 'true')
            self._set_raw_lua_value(edition, 'chips', '50')
        elif normalized_name == 'holo':
            self._set_raw_lua_value(edition, 'holo', 'true')
            self._set_raw_lua_value(edition, 'mult', '10')
        elif normalized_name == 'polychrome':
            self._set_raw_lua_value(edition, 'polychrome', 'true')
            self._set_raw_lua_value(edition, 'x_mult', '1.5')
        elif normalized_name == 'negative':
            self._set_raw_lua_value(edition, 'negative', 'true')
        return True

    def _set_seal_on_card(self, card, seal_name):
        if seal_name is None or str(seal_name).strip() == '':
            if 'seal' in card:
                self._remove_map_key(card, 'seal')
            return True

        card['seal'] = str(seal_name).title()
        return True

    def _set_sticker_on_card(self, card, sticker_name, enabled):
        if sticker_name == 'pinned':
            card['pinned'] = 'true' if enabled else 'false'
            return True
        if 'ability' not in card:
            return False
        card['ability'][sticker_name] = 'true' if enabled else 'false'
        return True

    def _ensure_child_map(self, parent_map, key):
        if key in parent_map:
            try:
                return parent_map[key]
            except Exception:
                return None

        entry_text = f'["{key}"]={{}},'
        entry_tokens = re.split(r'([\[\]{},="\\\'])', entry_text)
        entry_iterator = TokenIterator(entry_tokens)
        new_entry = MapEntryStruct(entry_iterator, next(entry_iterator))
        parent_map.structs.insert(-1, new_entry)
        return parent_map[key] if key in parent_map else None

    @staticmethod
    def _lua_string_literal(value):
        escaped = str(value).replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'

    def _normalize_lua_literal(self, value):
        text = str(value)
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
            quote_char = text[0]
            return text[1:-1].replace('\\' + quote_char, quote_char).replace('\\\\', '\\')
        return text

    def _remove_map_key(self, parent_map, key):
        removed = False
        for struct in list(parent_map.structs):
            if hasattr(struct, 'key') and struct.key == key:
                parent_map.structs.remove(struct)
                removed = True
        return removed

    def _insert_raw_map_entry(self, parent_map, key, raw_lua_value):
        encoded_key = str(key).replace('\\', '\\\\').replace('"', '\\"')
        entry_text = f'["{encoded_key}"]={raw_lua_value},'
        entry_tokens = re.split(r'([\[\]{},="\\\'])', entry_text)
        entry_iterator = TokenIterator(entry_tokens)
        new_entry = MapEntryStruct(entry_iterator, next(entry_iterator))
        parent_map.structs.insert(-1, new_entry)

    def _set_raw_lua_value(self, parent_map, key, raw_lua_value):
        self._remove_map_key(parent_map, key)
        self._insert_raw_map_entry(parent_map, key, raw_lua_value)

    def _set_string_field(self, parent_map, key, value):
        expected = '' if value is None else str(value)
        try:
            if key in parent_map:
                current = self._normalize_lua_literal(parent_map[key])
                if str(current) == expected:
                    return False
        except Exception:
            pass
        self._set_raw_lua_value(parent_map, key, self._lua_string_literal(expected))
        return True

    def _sync_consumeable_ability(self, ability_map, consumeable_config=None):
        changed = False
        defaults = consumeable_config or {}

        consumeable_node = None
        try:
            if 'consumeable' in ability_map:
                consumeable_node = ability_map['consumeable']
        except Exception:
            consumeable_node = None

        if not self._is_map_struct(consumeable_node):
            self._set_raw_lua_value(ability_map, 'consumeable', '{}')
            changed = True
            consumeable_node = self._ensure_child_map(ability_map, 'consumeable')

        if consumeable_node is None or not self._is_map_struct(consumeable_node):
            return changed

        if not defaults:
            return changed

        desired_keys = {str(key) for key in defaults.keys()}
        for struct in list(consumeable_node.structs):
            if hasattr(struct, 'key') and struct.key not in desired_keys:
                consumeable_node.structs.remove(struct)
                changed = True

        for key, raw_value in defaults.items():
            key_text = str(key)
            raw_text = str(raw_value)
            has_same_value = False
            try:
                if key_text in consumeable_node and str(consumeable_node[key_text]) == raw_text:
                    has_same_value = True
            except Exception:
                has_same_value = False

            if not has_same_value:
                self._set_raw_lua_value(consumeable_node, key_text, raw_text)
                changed = True

        return changed

    def _to_int_literal(self, value, default=0):
        try:
            parsed = self._parse_literal(value)
            return int(float(parsed))
        except Exception:
            return int(default)

    def _is_truthy_literal(self, value):
        normalized = str(self._normalize_lua_literal(value)).strip().lower()
        return normalized not in ('', 'false', 'nil', '0')

    def _normalize_card_edition_state(self, card):
        if 'edition' not in card:
            return False

        edition = card['edition']
        selected_type = None

        if 'type' in edition:
            t = self._normalize_lua_literal(edition['type']).strip().lower()
            alias = {'holographic': 'holo'}.get(t, t)
            if alias in ('foil', 'holo', 'polychrome', 'negative'):
                selected_type = alias

        if selected_type is None:
            candidates = (
                ('foil', 'foil'),
                ('holo', 'holo'),
                ('holographic', 'holo'),
                ('polychrome', 'polychrome'),
                ('negative', 'negative'),
            )
            for key_name, mapped in candidates:
                if key_name in edition and self._is_truthy_literal(edition[key_name]):
                    selected_type = mapped
                    break

        if selected_type is None:
            self._remove_map_key(card, 'edition')
            return True

        return self._set_edition_on_card(card, selected_type)

    def _count_negative_editions(self, area_name):
        count = 0
        try:
            for _key, card in self._iter_cards(area_name):
                if 'edition' not in card:
                    continue
                edition = card['edition']
                edition_type = self._normalize_lua_literal(edition['type']) if 'type' in edition else ''
                is_negative_flag = self._normalize_lua_literal(edition['negative']) == 'true' if 'negative' in edition else False
                if edition_type == 'negative' or is_negative_flag:
                    count += 1
        except Exception:
            return 0
        return count

    def _scale_game_probabilities(self, factor):
        changed = False
        if factor == 1:
            return False
        try:
            probabilities = self._get_by_path(['GAME', 'probabilities'])
        except Exception:
            return False

        for key, value in self._iter_map_entries(probabilities):
            try:
                parsed = float(self._normalize_lua_literal(value))
                scaled = parsed * factor
                if abs(scaled - round(scaled)) < 1e-9:
                    probabilities[key] = str(int(round(scaled)))
                else:
                    probabilities[key] = str(scaled)
                changed = True
            except Exception:
                continue
        return changed

    def reconcile_negative_card_limits(self):
        changed = False
        try:
            joker_base_slots = self._to_int_literal(self._get_by_path(['GAME', 'starting_params', 'joker_slots']), default=5)
        except Exception:
            joker_base_slots = 5
        try:
            consumable_base_slots = self._to_int_literal(self._get_by_path(['GAME', 'starting_params', 'consumable_slots']), default=2)
        except Exception:
            consumable_base_slots = 2

        required_joker_limit = joker_base_slots + self._count_negative_editions('jokers')
        required_consumable_limit = consumable_base_slots + self._count_negative_editions('consumeables')

        targets = [
            ('jokers', required_joker_limit),
            ('consumeables', required_consumable_limit),
        ]

        for area_name, required_limit in targets:
            try:
                config = self._get_by_path(['cardAreas', area_name, 'config'])
            except Exception:
                continue

            for key in ('card_limit', 'temp_limit'):
                current_value = required_limit
                if key in config:
                    current_value = self._to_int_literal(config[key], default=required_limit)
                if current_value < required_limit:
                    config[key] = str(required_limit)
                    changed = True
                elif key not in config:
                    config[key] = str(required_limit)
                    changed = True

        return changed

    @staticmethod
    def _is_map_struct(value):
        return isinstance(value, MapStruct)

    def _root_map(self):
        return self.balatro_save_file.structs[1]

    def _ensure_child_map_struct(self, parent_map, key):
        if key not in parent_map:
            self._set_raw_lua_value(parent_map, key, '{}')
            return parent_map[key]

        current = parent_map[key]
        if self._is_map_struct(current):
            return current

        self._set_raw_lua_value(parent_map, key, '{}')
        return parent_map[key]

    def _guess_playing_card_from_proto(self, card):
        try:
            if 'save_fields' not in card or 'card' not in card['save_fields']:
                return False
            proto = self._normalize_lua_literal(card['save_fields']['card'])
            if proto in ('', 'nil', 'empty'):
                return False
            return bool(re.match(r'^[HCDS]_[2-9TJQKA]$', proto))
        except Exception:
            return False

    def _is_playing_card(self, card):
        if 'playing_card' in card:
            playing_card_text = card['playing_card']
            normalized = str(self._normalize_lua_literal(playing_card_text)).strip().lower()
            if normalized in ('', 'false', 'nil'):
                return False
            return True
        return self._guess_playing_card_from_proto(card)

    def ensure_required_card_areas(self):
        changed = False

        root = self._root_map()
        card_areas = self._ensure_child_map_struct(root, 'cardAreas')

        default_types = {
            'jokers': 'joker',
            'deck': 'deck',
            'hand': 'hand',
            'consumeables': 'joker',
        }

        default_limits = {
            'jokers': ('GAME', 'starting_params', 'joker_slots', '5'),
            'deck': (None, None, None, '52'),
            'hand': ('GAME', 'starting_params', 'hand_size', '8'),
            'consumeables': ('GAME', 'starting_params', 'consumable_slots', '2'),
        }

        for area_name in ('jokers', 'deck', 'hand', 'consumeables'):
            if area_name not in card_areas:
                changed = True
            area = self._ensure_child_map_struct(card_areas, area_name)

            if 'cards' not in area:
                changed = True
            self._ensure_child_map_struct(area, 'cards')

            if 'config' not in area:
                changed = True
            config = self._ensure_child_map_struct(area, 'config')

            changed = self._ensure_literal_default(config, 'type', self._lua_string_literal(default_types[area_name])) or changed

            path_a, path_b, path_c, fallback_limit = default_limits[area_name]
            desired_limit = fallback_limit
            if path_a is not None:
                try:
                    desired_limit = str(self._get_by_path([path_a, path_b, path_c]))
                except Exception:
                    desired_limit = fallback_limit

            changed = self._ensure_literal_default(config, 'card_limit', desired_limit) or changed
            changed = self._ensure_literal_default(config, 'temp_limit', desired_limit) or changed

        return changed

    def _ensure_literal_default(self, parent_map, key, raw_lua_value):
        if key not in parent_map:
            self._set_raw_lua_value(parent_map, key, raw_lua_value)
            return True

        try:
            current = parent_map[key]
        except Exception:
            self._set_raw_lua_value(parent_map, key, raw_lua_value)
            return True

        if self._is_map_struct(current):
            return False

        current_text = self._normalize_lua_literal(current)
        if current_text == 'nil':
            self._set_raw_lua_value(parent_map, key, raw_lua_value)
            return True
        return False

    def _ensure_map_default_from_template(self, parent_map, key, template_map=None):
        if key in parent_map:
            return False

        if template_map is not None and key in template_map:
            self._set_raw_lua_value(parent_map, key, str(template_map[key]))
            return True

        return False

    def ensure_card_core_fields(self, card, template_card=None):
        changed = False

        changed = self._ensure_map_default_from_template(card, 'save_fields', template_card) or changed
        changed = self._ensure_map_default_from_template(card, 'ability', template_card) or changed
        changed = self._ensure_map_default_from_template(card, 'base', template_card) or changed

        base = self._ensure_child_map(card, 'base')
        if base is None:
            return changed

        template_base = None
        try:
            if template_card is not None and 'base' in template_card:
                template_base = template_card['base']
        except Exception:
            template_base = None

        is_playing_card = self._is_playing_card(card)

        if is_playing_card:
            proto_suit = None
            proto_rank = None
            try:
                if 'save_fields' in card and 'card' in card['save_fields']:
                    proto = self._normalize_lua_literal(card['save_fields']['card'])
                    if isinstance(proto, str) and '_' in proto:
                        suit_code, rank_code = proto.split('_', 1)
                        proto_suit = self._proto_to_suit(suit_code)
                        proto_rank = self._proto_to_rank(rank_code)
            except Exception:
                proto_suit = None
                proto_rank = None

            for required_key in ('suit', 'value'):
                default_raw = None
                if required_key == 'suit' and proto_suit is not None:
                    default_raw = self._lua_string_literal(proto_suit)
                if required_key == 'value' and proto_rank is not None:
                    default_raw = self._lua_string_literal(proto_rank)
                if template_base is not None and required_key in template_base:
                    if default_raw is None:
                        default_raw = str(template_base[required_key])
                if default_raw is not None:
                    changed = self._ensure_literal_default(base, required_key, default_raw) or changed

            suit_value = self._normalize_lua_literal(base['suit']) if 'suit' in base else proto_suit
            rank_value = self._normalize_lua_literal(base['value']) if 'value' in base else proto_rank

            if suit_value and rank_value:
                changed = self._ensure_literal_default(base, 'name', self._lua_string_literal(f'{rank_value} of {suit_value}')) or changed
                computed_id = self._base_id(rank_value)
                if computed_id is not None:
                    changed = self._ensure_literal_default(base, 'id', str(computed_id)) or changed
                changed = self._ensure_literal_default(base, 'nominal', self._nominal(rank_value)) or changed
                changed = self._ensure_literal_default(base, 'face_nominal', self._face_nominal(rank_value)) or changed
                suit_nominal = self._suit_nominal(suit_value)
                if suit_nominal is not None:
                    changed = self._ensure_literal_default(base, 'suit_nominal', suit_nominal) or changed
                suit_nominal_original = self._suit_nominal_original(suit_value)
                if suit_nominal_original is not None:
                    changed = self._ensure_literal_default(base, 'suit_nominal_original', suit_nominal_original) or changed
                changed = self._ensure_literal_default(base, 'original_value', self._lua_string_literal(rank_value)) or changed
                changed = self._ensure_literal_default(base, 'times_played', '0') or changed
        else:
            for key in ('suit', 'value', 'name', 'id', 'colour'):
                if self._remove_map_key(base, key):
                    changed = True
            
            for key in ('nominal', 'suit_nominal', 'face_nominal', 'times_played'):
                changed = self._ensure_literal_default(base, key, '0') or changed

        return changed

    def _ensure_extra_schema(self, ability_map, center_def):
        expected_extra = center_def.extra_default
        if expected_extra is None:
            return False

        expected_is_map = str(expected_extra).strip().startswith('{')

        if 'extra' not in ability_map:
            self._set_raw_lua_value(ability_map, 'extra', expected_extra)
            return True

        try:
            current = ability_map['extra']
        except Exception:
            self._set_raw_lua_value(ability_map, 'extra', expected_extra)
            return True

        current_is_map = self._is_map_struct(current)
        current_text = self._normalize_lua_literal(current)

        if current_text == 'nil':
            self._set_raw_lua_value(ability_map, 'extra', expected_extra)
            return True
        if expected_is_map and not current_is_map:
            self._set_raw_lua_value(ability_map, 'extra', expected_extra)
            return True
        if (not expected_is_map) and current_is_map:
            self._set_raw_lua_value(ability_map, 'extra', expected_extra)
            return True
        return False

    def ensure_card_schema(self, card, game_catalog=None):
        if game_catalog is None:
            return False

        changed = False
        changed = self._normalize_card_edition_state(card) or changed
        save_fields = self._ensure_child_map(card, 'save_fields')
        if save_fields is None or 'center' not in save_fields:
            return False

        center_id = self._normalize_lua_literal(save_fields['center'])
        center_def = game_catalog.centers.get(center_id)
        if center_def is None:
            return False

        ability = self._ensure_child_map(card, 'ability')
        if ability is None:
            return False

        changed = self._set_string_field(ability, 'name', center_def.name) or changed
        changed = self._set_string_field(ability, 'effect', center_def.effect or '') or changed
        changed = self._set_string_field(ability, 'set', center_def.set_name or '') or changed

        if center_def.set_name in ('Tarot', 'Planet', 'Spectral'):
            changed = self._sync_consumeable_ability(
                ability,
                consumeable_config=center_def.config_defaults,
            ) or changed

        cfg = center_def.config_defaults or {}
        defaults = {
            'mult': cfg.get('mult', '0'),
            'h_mult': cfg.get('h_mult', '0'),
            'h_x_mult': cfg.get('h_x_mult', '0'),
            'h_dollars': cfg.get('h_dollars', '0'),
            'p_dollars': cfg.get('p_dollars', '0'),
            't_mult': cfg.get('t_mult', '0'),
            't_chips': cfg.get('t_chips', '0'),
            'bonus': cfg.get('bonus', '0'),
            'x_mult': cfg.get('Xmult', '1'),
            'h_size': cfg.get('h_size', '0'),
            'd_size': cfg.get('d_size', '0'),
            'type': cfg.get('type', '""'),
            'extra_value': '0',
            'perma_bonus': '0',
        }

        for key, raw_value in defaults.items():
            changed = self._ensure_literal_default(ability, key, raw_value) or changed

        if center_def.order is not None:
            changed = self._ensure_literal_default(ability, 'order', str(center_def.order)) or changed

        changed = self._ensure_extra_schema(ability, center_def) or changed
        
        # Hardcoded dynamic fields from Card:set_ability
        changed = self._ensure_literal_default(ability, 'hands_played_at_create', '0') or changed

        if center_def.name == "Invisible Joker":
            changed = self._ensure_literal_default(ability, 'invis_rounds', '0') or changed
        elif center_def.name == "To Do List":
            changed = self._ensure_literal_default(ability, 'to_do_poker_hand', '"High Card"') or changed
        elif center_def.name == "Caino":
            changed = self._ensure_literal_default(ability, 'caino_xmult', '1') or changed
        elif center_def.name == "Yorick":
            discards = '0'
            try:
                if 'extra' in ability and self._is_map_struct(ability['extra']) and 'discards' in ability['extra']:
                    discards = self._normalize_lua_literal(ability['extra']['discards'])
            except Exception:
                discards = '0'
            changed = self._ensure_literal_default(ability, 'yorick_discards', str(discards)) or changed
        elif center_def.name == "Loyalty Card":
            changed = self._ensure_literal_default(ability, 'burnt_hand', '0') or changed
            every = '0'
            try:
                if 'extra' in ability and self._is_map_struct(ability['extra']) and 'every' in ability['extra']:
                    every = self._normalize_lua_literal(ability['extra']['every'])
            except Exception:
                every = '0'
            changed = self._ensure_literal_default(ability, 'loyalty_remaining', str(every)) or changed

        return changed

    def ensure_all_card_schemas(self, game_catalog=None):
        if game_catalog is None:
            return 0

        self.ensure_required_card_areas()

        changed_cards = 0
        for area_name in ('jokers', 'deck', 'hand', 'consumeables'):
            try:
                template_card = None
                try:
                    _template_key, template_card = self._get_card_by_position(area_name, 1)
                except Exception:
                    template_card = None

                for _key, card in self._iter_cards(area_name):
                    core_changed = self.ensure_card_core_fields(card, template_card=template_card)
                    schema_changed = self.ensure_card_schema(card, game_catalog=game_catalog)
                    if core_changed or schema_changed:
                        changed_cards += 1
            except Exception:
                continue

        if self.reconcile_negative_card_limits():
            changed_cards += 1
        return changed_cards

    def _default_card_proto_for_area(self, area_name):
        try:
            for _key, card in self._iter_cards(area_name):
                if 'save_fields' in card and 'card' in card['save_fields']:
                    return str(self._parse_literal(card['save_fields']['card']))
        except Exception:
            pass
        return None

    def _reindex_card_area(self, area_name):
        cards_map = self._card_area_cards(area_name)
        ordered_cards = [card for _key, card in self._iter_map_entries(cards_map)]

        rebuilt = '{' + ''.join(
            f'[{index}]={str(card)},' for index, card in enumerate(ordered_cards, start=1)
        ) + '}'

        tokens = re.split(r'([\[\]{},="\\\'])', rebuilt)
        token_iterator = TokenIterator(tokens)
        rebuilt_map = MapStruct(token_iterator, next(token_iterator))
        cards_map.structs = rebuilt_map.structs

    @staticmethod
    def _rank_to_proto(value):
        mapping = {
            '2': '2',
            '3': '3',
            '4': '4',
            '5': '5',
            '6': '6',
            '7': '7',
            '8': '8',
            '9': '9',
            '10': 'T',
            'Jack': 'J',
            'Queen': 'Q',
            'King': 'K',
            'Ace': 'A',
        }
        return mapping.get(str(value))

    @staticmethod
    def _proto_to_rank(value):
        mapping = {
            '2': '2',
            '3': '3',
            '4': '4',
            '5': '5',
            '6': '6',
            '7': '7',
            '8': '8',
            '9': '9',
            'T': '10',
            'J': 'Jack',
            'Q': 'Queen',
            'K': 'King',
            'A': 'Ace',
        }
        return mapping.get(str(value))

    @staticmethod
    def _suit_to_proto(value):
        mapping = {
            'Hearts': 'H',
            'Clubs': 'C',
            'Diamonds': 'D',
            'Spades': 'S',
        }
        return mapping.get(str(value))

    @staticmethod
    def _proto_to_suit(value):
        mapping = {
            'H': 'Hearts',
            'C': 'Clubs',
            'D': 'Diamonds',
            'S': 'Spades',
        }
        return mapping.get(str(value))

    @staticmethod
    def _face_nominal(rank_value):
        if rank_value == 'Jack':
            return '0.1'
        if rank_value == 'Queen':
            return '0.2'
        if rank_value == 'King':
            return '0.3'
        if rank_value == 'Ace':
            return '0.4'
        return '0'

    @staticmethod
    def _nominal(rank_value):
        if rank_value in ('Jack', 'Queen', 'King'):
            return '10'
        if rank_value == 'Ace':
            return '11'
        return str(rank_value)

    @staticmethod
    def _base_id(rank_value):
        mapping = {
            '2': '2',
            '3': '3',
            '4': '4',
            '5': '5',
            '6': '6',
            '7': '7',
            '8': '8',
            '9': '9',
            '10': '10',
            'Jack': '11',
            'Queen': '12',
            'King': '13',
            'Ace': '14',
        }
        return mapping.get(rank_value)

    @staticmethod
    def _suit_nominal(suit_value):
        mapping = {
            'Diamonds': '0.01',
            'Clubs': '0.02',
            'Hearts': '0.03',
            'Spades': '0.04',
        }
        return mapping.get(suit_value)

    @staticmethod
    def _suit_nominal_original(suit_value):
        mapping = {
            'Diamonds': '0.001',
            'Clubs': '0.002',
            'Hearts': '0.003',
            'Spades': '0.004',
        }
        return mapping.get(suit_value)

    def _card_proto_parts(self, card):
        try:
            proto = self._parse_literal(card['save_fields']['card'])
            if not isinstance(proto, str) or '_' not in proto:
                return None, None
            suit_code, rank_code = proto.split('_', 1)
            return suit_code, rank_code
        except Exception:
            return None, None

    def _set_card_face_on_card(self, card, suit=None, rank=None):
        suit_code, rank_code = self._card_proto_parts(card)
        if not suit_code or not rank_code:
            return False

        target_suit = suit or self._proto_to_suit(suit_code)
        target_rank = rank or self._proto_to_rank(rank_code)

        target_suit_code = self._suit_to_proto(target_suit)
        target_rank_code = self._rank_to_proto(target_rank)
        if not target_suit_code or not target_rank_code:
            return False

        card['save_fields']['card'] = f'{target_suit_code}_{target_rank_code}'

        if 'base' in card:
            base = card['base']
            if 'suit' in base:
                base['suit'] = target_suit
            if 'value' in base:
                base['value'] = target_rank
            if 'name' in base:
                base['name'] = f'{target_rank} of {target_suit}'
            if 'id' in base:
                computed = self._base_id(target_rank)
                if computed is not None:
                    base['id'] = computed
            if 'nominal' in base:
                base['nominal'] = self._nominal(target_rank)
            if 'face_nominal' in base:
                base['face_nominal'] = self._face_nominal(target_rank)
            if 'suit_nominal' in base:
                computed = self._suit_nominal(target_suit)
                if computed is not None:
                    base['suit_nominal'] = computed
            if 'suit_nominal_original' in base:
                computed = self._suit_nominal_original(target_suit)
                if computed is not None:
                    base['suit_nominal_original'] = computed
            if 'original_value' in base:
                base['original_value'] = target_rank
        return True

    def set_card_face(self, area_name, card_index, suit=None, rank=None):
        _key, card = self._get_card_by_position(area_name, card_index)
        return self._set_card_face_on_card(card, suit=suit, rank=rank)

    def set_card_enhancement(self, area_name, card_index, center_id, center_name=None, center_effect=None):
        _key, card = self._get_card_by_position(area_name, card_index)
        if 'save_fields' not in card or 'center' not in card['save_fields']:
            return False
        card['save_fields']['center'] = center_id

        self._set_raw_lua_value(card, 'ability', '{}')
        ability = self._ensure_child_map(card, 'ability')
        if ability is None:
            return False

        ability['set'] = 'Enhanced'
        if center_name is not None:
            ability['name'] = center_name
        if center_effect is not None:
            ability['effect'] = center_effect
        if center_name is not None and 'label' in card:
            card['label'] = center_name
        return True

    def clear_card_enhancement(self, area_name, card_index, center_id='c_base', center_name=None, center_effect=None):
        _key, card = self._get_card_by_position(area_name, card_index)
        if 'save_fields' not in card or 'center' not in card['save_fields']:
            return False
        card['save_fields']['center'] = center_id

        self._set_raw_lua_value(card, 'ability', '{}')
        ability = self._ensure_child_map(card, 'ability')
        if ability is None:
            return False

        ability['set'] = 'Default'
        if center_name is not None:
            ability['name'] = center_name
        if center_effect is not None:
            ability['effect'] = center_effect
        else:
            self._remove_map_key(ability, 'effect')
        if center_name is not None and 'label' in card:
            card['label'] = center_name
        return True

    def _card_display_name(self, card, fallback='Unknown'):
        try:
            if 'ability' in card and 'name' in card['ability']:
                return str(self._parse_literal(card['ability']['name']))
        except Exception:
            pass
        return fallback

    def _card_center_id(self, card):
        try:
            if 'save_fields' in card and 'center' in card['save_fields']:
                return str(self._parse_literal(card['save_fields']['center']))
        except Exception:
            pass
        return None

    def _card_save_id(self, card):
        try:
            if 'save_fields' in card and 'id' in card['save_fields']:
                return str(self._parse_literal(card['save_fields']['id']))
        except Exception:
            pass
        return None

    def _card_proto_id(self, card):
        try:
            if 'save_fields' in card and 'card' in card['save_fields']:
                return str(self._parse_literal(card['save_fields']['card']))
        except Exception:
            pass
        return None

    def _card_base_field(self, card, key):
        try:
            if 'base' in card and key in card['base']:
                return str(self._parse_literal(card['base'][key]))
        except Exception:
            pass
        return None

    def list_cards(self, area_name):
        cards = []
        idx = 1
        for key, card in self._iter_cards(area_name):
            edition_type = None
            seal = None
            stickers = {}
            center_id = self._card_center_id(card)
            save_id = self._card_save_id(card)
            card_proto = self._card_proto_id(card)
            base_suit = self._card_base_field(card, 'suit')
            base_value = self._card_base_field(card, 'value')

            if 'edition' in card and 'type' in card['edition']:
                edition_type = str(self._parse_literal(card['edition']['type']))
            if 'seal' in card:
                seal = str(self._parse_literal(card['seal']))

            if 'ability' in card:
                for sticker in ('eternal', 'perishable', 'rental'):
                    if sticker in card['ability']:
                        stickers[sticker] = self._parse_literal(card['ability'][sticker]) is True
            if 'pinned' in card:
                stickers['pinned'] = self._parse_literal(card['pinned']) is True

            cards.append(
                {
                    'index': idx,
                    'key': key,
                    'name': self._card_display_name(card),
                    'center_id': center_id,
                    'save_id': save_id,
                    'card_proto': card_proto,
                    'base_suit': base_suit,
                    'base_value': base_value,
                    'id': save_id or center_id or card_proto,
                    'edition': edition_type,
                    'seal': seal,
                    'stickers': stickers,
                }
            )
            idx += 1
        return cards

    def get_card_modification_preview(self, area_name, card_index, edition=None, seal=None, stickers=None):
        _key, card = self._get_card_by_position(area_name, card_index)
        current = {
            'edition': self._parse_literal(card['edition']['type']) if ('edition' in card and 'type' in card['edition']) else None,
            'seal': self._parse_literal(card['seal']) if 'seal' in card else None,
            'stickers': {
                'eternal': self._parse_literal(card['ability']['eternal']) if ('ability' in card and 'eternal' in card['ability']) else None,
                'perishable': self._parse_literal(card['ability']['perishable']) if ('ability' in card and 'perishable' in card['ability']) else None,
                'rental': self._parse_literal(card['ability']['rental']) if ('ability' in card and 'rental' in card['ability']) else None,
                'pinned': self._parse_literal(card['pinned']) if 'pinned' in card else None,
            },
        }

        target = {
            'edition': edition if edition is not None else current['edition'],
            'seal': seal if seal is not None else current['seal'],
            'stickers': dict(current['stickers']),
        }
        if stickers:
            target['stickers'].update(stickers)
        return {'old': current, 'new': target}

    def set_card_modifiers(self, area_name, card_index, edition=None, seal=None, stickers=None):
        _key, card = self._get_card_by_position(area_name, card_index)
        changed = 0

        if edition is not None:
            if self._set_edition_on_card(card, edition):
                changed += 1
        if seal is not None:
            if self._set_seal_on_card(card, seal):
                changed += 1
        if stickers:
            for sticker_key, sticker_enabled in stickers.items():
                if self._set_sticker_on_card(card, sticker_key, bool(sticker_enabled)):
                    changed += 1
        return changed

    def _next_card_key(self, area_name):
        max_key = 0
        for key, _card in self._iter_cards(area_name):
            try:
                max_key = max(max_key, int(str(key)))
            except ValueError:
                continue
        return str(max_key + 1)

    def add_card_clone(self, area_name, source_index=1, source_area=None):
        source_area_name = source_area or area_name
        source_key, source_card = self._get_card_by_position(source_area_name, source_index)
        cards_map = self._card_area_cards(area_name)
        new_key = self._next_card_key(area_name)

        entry_text = f'[{new_key}]={str(source_card)},'
        entry_tokens = re.split(r'([\[\]{},="\\])', entry_text)
        entry_iterator = TokenIterator(entry_tokens)
        new_entry = MapEntryStruct(entry_iterator, next(entry_iterator))
        cards_map.structs.insert(-1, new_entry)
        self._reindex_card_area(area_name)
        new_key = str(self.get_card_count(area_name))
        return new_key, source_key

    def add_joker_by_center(self, center_id, center_name=None, center_effect=None):
        self.ensure_required_card_areas()

        def next_sort_id():
            max_sort_id = 0
            for area_name in ('jokers', 'deck', 'hand', 'consumeables'):
                try:
                    for _key, area_card in self._iter_cards(area_name):
                        if 'sort_id' in area_card:
                            try:
                                max_sort_id = max(max_sort_id, int(str(area_card['sort_id'])))
                            except Exception:
                                continue
                except Exception:
                    continue
            return max_sort_id + 1

        source_area = None
        source_template = None
        for candidate_area in ('jokers', 'deck', 'hand'):
            try:
                _template_key, candidate_template = self._get_card_by_position(candidate_area, 1)
                if 'save_fields' in candidate_template and 'ability' in candidate_template and 'base' in candidate_template:
                    source_area = candidate_area
                    source_template = candidate_template
                    break
                if source_area is None:
                    source_area = candidate_area
                    source_template = candidate_template
            except Exception:
                continue

        if source_area is None:
            raise ValueError('No card template is available to create a new Joker.')

        new_key, _source_key = self.add_card_clone('jokers', source_index=1, source_area=source_area)

        card = self._card_area_cards('jokers')[new_key]

        if 'save_fields' in card and 'center' in card['save_fields']:
            card['save_fields']['center'] = center_id
            card['save_fields']['card'] = 'nil'
        self._set_raw_lua_value(card, 'ability', '{}')

        if 'edition' in card:
            self._remove_map_key(card, 'edition')
        if 'seal' in card:
            self._remove_map_key(card, 'seal')
        if 'ability' in card:
            for sticker_key in ('eternal', 'perishable', 'rental'):
                if sticker_key in card['ability']:
                    self._remove_map_key(card['ability'], sticker_key)

        if 'sort_id' in card:
            card['sort_id'] = str(next_sort_id())
        if 'ability' in card:
            self._set_string_field(card['ability'], 'set', 'Joker')
            if center_name is not None:
                self._set_string_field(card['ability'], 'name', center_name)
            if center_effect is not None:
                self._set_string_field(card['ability'], 'effect', center_effect)
        card['playing_card'] = 'false'
        card['facing'] = 'front'
        card['sprite_facing'] = 'front'
        card['flipping'] = 'nil'
        card['highlighted'] = 'false'
        card['debuff'] = 'false'
        card['pinned'] = 'false'
        card['added_to_deck'] = 'true'

        if center_name == 'Oops! All 6s':
            self._scale_game_probabilities(2)

        self.ensure_card_core_fields(card, template_card=source_template)
        return new_key

    def add_consumeable_by_center(self, center_id, center_name=None, center_set=None, center_effect=None, consumeable_config=None):
        self.ensure_required_card_areas()

        def next_sort_id():
            max_sort_id = 0
            for area_name in ('jokers', 'deck', 'hand', 'consumeables'):
                try:
                    for _key, area_card in self._iter_cards(area_name):
                        if 'sort_id' in area_card:
                            try:
                                max_sort_id = max(max_sort_id, int(str(area_card['sort_id'])))
                            except Exception:
                                continue
                except Exception:
                    continue
            return max_sort_id + 1

        source_area = None
        source_template = None
        for candidate_area in ('consumeables', 'jokers', 'deck', 'hand'):
            try:
                _template_key, candidate_template = self._get_card_by_position(candidate_area, 1)
                source_area = candidate_area
                source_template = candidate_template
                break
            except Exception:
                continue

        if source_area is None:
            raise ValueError('No card template is available to create a new consumeable.')

        new_key, _source_key = self.add_card_clone('consumeables', source_index=1, source_area=source_area)
        card = self._card_area_cards('consumeables')[new_key]

        if 'save_fields' in card:
            if 'center' in card['save_fields']:
                card['save_fields']['center'] = center_id
            if 'card' in card['save_fields']:
                card['save_fields']['card'] = 'nil'

        ability = self._ensure_child_map(card, 'ability')
        if ability is not None:
            set_name = center_set or 'Tarot'
            self._set_string_field(ability, 'set', set_name)
            self._set_string_field(ability, 'name', center_name or center_id)
            self._set_string_field(ability, 'effect', center_effect or '')
            self._sync_consumeable_ability(ability, consumeable_config=consumeable_config)

            for sticker_key in ('eternal', 'perishable', 'rental'):
                if sticker_key in ability:
                    self._remove_map_key(ability, sticker_key)

        if 'edition' in card:
            self._remove_map_key(card, 'edition')
        if 'seal' in card:
            self._remove_map_key(card, 'seal')

        if 'sort_id' in card:
            card['sort_id'] = str(next_sort_id())
        card['playing_card'] = 'false'
        card['facing'] = 'front'
        card['sprite_facing'] = 'front'
        card['flipping'] = 'nil'
        card['highlighted'] = 'false'
        card['debuff'] = 'false'
        card['pinned'] = 'false'
        card['added_to_deck'] = 'true'

        self.ensure_card_core_fields(card, template_card=source_template)
        return new_key

    def apply_card_edition(self, area_name, edition_name, apply_all=False, card_index=None):
        changed = 0
        if apply_all:
            for _key, card in self._iter_cards(area_name):
                if self._set_edition_on_card(card, edition_name):
                    changed += 1
            return changed

        _key, card = self._get_card_by_position(area_name, card_index)
        if self._set_edition_on_card(card, edition_name):
            changed += 1
        return changed

    def apply_card_seal(self, area_name, seal_name, apply_all=False, card_index=None):
        changed = 0
        if apply_all:
            for _key, card in self._iter_cards(area_name):
                if self._set_seal_on_card(card, seal_name):
                    changed += 1
            return changed

        _key, card = self._get_card_by_position(area_name, card_index)
        if self._set_seal_on_card(card, seal_name):
            changed += 1
        return changed

    def apply_card_sticker(self, area_name, sticker_name, enabled, apply_all=False, card_index=None):
        changed = 0
        if apply_all:
            for _key, card in self._iter_cards(area_name):
                if self._set_sticker_on_card(card, sticker_name, enabled):
                    changed += 1
            return changed

        _key, card = self._get_card_by_position(area_name, card_index)
        if self._set_sticker_on_card(card, sticker_name, enabled):
            changed += 1
        return changed

    def list_active_vouchers(self):
        active = []
        vouchers = self.balatro_save_file['GAME']['used_vouchers']
        for key, value in self._iter_map_entries(vouchers):
            if str(value) == 'true':
                active.append(key)
        return active

    def list_voucher_keys(self):
        keys = []
        vouchers = self.balatro_save_file['GAME']['used_vouchers']
        for key, _value in self._iter_map_entries(vouchers):
            keys.append(key)
        return keys

    def unlock_all_vouchers(self):
        count = 0
        vouchers = self.balatro_save_file['GAME']['used_vouchers']
        for key, _value in self._iter_map_entries(vouchers):
            vouchers[key] = 'true'
            count += 1
        return count

    def set_voucher(self, voucher_key, enabled):
        vouchers = self.balatro_save_file['GAME']['used_vouchers']
        vouchers[voucher_key] = 'true' if enabled else 'false'

    def set_probability_denominator(self, value):
        self._set_by_path(['GAME', 'probabilities', 'normal'], value)

    def set_seed(self, seed_value):
        self._set_by_path(['GAME', 'pseudorandom', 'seed'], seed_value)

    def force_100_rng(self):
        self.set_probability_denominator(1)

    def god_infinite_everything(self):
        self.set_money(999999999)
        self.set_interest_cap(999999)
        self.set_joker_slots(999)
        self.set_consumable_slots(999)
        self.set_hand_size(50)
        self.set_hands_left(99)
        self.set_discards_left(99)
        self.set_reroll_cost(0)
        self.set_blind_requirement(1)
        self.edit_multipliers(new_mult=100000)
        self.edit_card_limits()

    def god_all_negative_jokers(self):
        return self.apply_card_edition('jokers', 'negative', apply_all=True)

    def god_max_all_hands(self):
        return self.max_all_hands()

    def god_free_shop(self):
        self.set_reroll_cost(0)

    def god_guaranteed_rng(self):
        self.force_100_rng()

    def god_unlock_everything(self):
        self.unlock_all_vouchers()
        self.edit_card_limits()
        self.edit_card_abilities()
