import re


class SaveStructureValidator(object):
    def __init__(self, game_catalog):
        self.catalog = game_catalog

    @staticmethod
    def _normalize_literal(value):
        text = str(value)
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
            quote_char = text[0]
            text = text[1:-1].replace('\\' + quote_char, quote_char).replace('\\\\', '\\')
        return text

    @staticmethod
    def _is_bool_literal(value):
        return SaveStructureValidator._normalize_literal(value) in ('true', 'false')

    @staticmethod
    def _is_map_value(value):
        return hasattr(value, 'structs') and len(value.structs) > 0 and str(value.structs[0]) == '{'

    @staticmethod
    def _is_valid_facing(value):
        return SaveStructureValidator._normalize_literal(value) in ('front', 'back')

    def _is_playing_card(self, card):
        if 'playing_card' in card:
            normalized = str(self._normalize_literal(card['playing_card'])).strip().lower()
            if normalized in ('', 'false', 'nil'):
                return False
            return True

        try:
            if 'save_fields' in card and 'card' in card['save_fields']:
                proto = self._normalize_literal(card['save_fields']['card'])
                return bool(re.match(r'^[HCDS]_[2-9TJQKA]$', proto))
        except Exception:
            return False
        return False

    def _validate_core_paths(self, editor):
        errors = []
        required_paths = [
            ['GAME', 'hands'],
            ['GAME', 'modifiers'],
            ['GAME', 'probabilities'],
            ['GAME', 'used_vouchers'],
            ['cardAreas'],
            ['cardAreas', 'jokers'],
            ['cardAreas', 'deck'],
            ['cardAreas', 'hand'],
            ['cardAreas', 'consumeables'],
        ]
        for keys in required_paths:
            try:
                editor._get_by_path(keys)
            except Exception:
                errors.append(f"Missing required path: {'.'.join(keys)}")

        for area_name in ('jokers', 'deck', 'hand', 'consumeables'):
            for suffix in (['cards'], ['config']):
                keys = ['cardAreas', area_name] + suffix
                try:
                    value = editor._get_by_path(keys)
                except Exception:
                    errors.append(f"Missing required path: {'.'.join(keys)}")
                    continue
                if not self._is_map_value(value):
                    errors.append(f"Invalid map at path: {'.'.join(keys)}")
        return errors

    def _validate_card_schema(self, card, area_name, index):
        errors = []

        if 'save_fields' not in card or 'center' not in card['save_fields']:
            errors.append(f'{area_name}[{index}] missing save_fields.center')
            return errors

        if 'facing' not in card:
            errors.append(f'{area_name}[{index}] missing facing')
        elif not self._is_valid_facing(card['facing']):
            errors.append(f'{area_name}[{index}] invalid facing value')

        if 'sprite_facing' not in card:
            errors.append(f'{area_name}[{index}] missing sprite_facing')
        elif not self._is_valid_facing(card['sprite_facing']):
            errors.append(f'{area_name}[{index}] invalid sprite_facing value')

        if area_name in ('deck', 'hand'):
            if 'save_fields' not in card or 'card' not in card['save_fields']:
                errors.append(f'{area_name}[{index}] missing save_fields.card')

        center_id = self._normalize_literal(card['save_fields']['center'])
        if center_id not in self.catalog.centers:
            errors.append(f'{area_name}[{index}] unknown center id: {center_id}')
        else:
            center_def = self.catalog.centers[center_id]
            set_name = self.catalog.center_set(center_id)
            if area_name == 'jokers' and set_name != 'Joker':
                errors.append(f'{area_name}[{index}] center {center_id} is not a Joker center')

            if 'ability' not in card:
                errors.append(f'{area_name}[{index}] missing ability map')
            else:
                ability = card['ability']
                for required_key in ('name', 'effect', 'set'):
                    if required_key not in ability:
                        errors.append(f'{area_name}[{index}] missing ability.{required_key}')

                if 'bonus' not in ability:
                    errors.append(f'{area_name}[{index}] missing ability.bonus')

                expected_extra = center_def.extra_default
                if expected_extra is not None:
                    expected_is_map = str(expected_extra).strip().startswith('{')
                    if 'extra' not in ability:
                        errors.append(f'{area_name}[{index}] missing ability.extra for center {center_id}')
                    else:
                        actual_extra = ability['extra']
                        actual_is_map = self._is_map_value(actual_extra)
                        if expected_is_map and not actual_is_map:
                            errors.append(f'{area_name}[{index}] ability.extra has wrong type for center {center_id} (expected table)')
                        if (not expected_is_map) and actual_is_map:
                            errors.append(f'{area_name}[{index}] ability.extra has wrong type for center {center_id} (expected scalar)')
                        if self._normalize_literal(actual_extra) == 'nil':
                            errors.append(f'{area_name}[{index}] ability.extra is nil for center {center_id}')

        if 'edition' in card:
            edition = card['edition']
            if 'type' not in edition:
                errors.append(f'{area_name}[{index}] edition exists but missing edition.type')
            else:
                edition_type = self._normalize_literal(edition['type'])
                if edition_type not in self.catalog.editions:
                    errors.append(f'{area_name}[{index}] invalid edition type: {edition_type}')

        if 'seal' in card:
            seal_value = self._normalize_literal(card['seal'])
            if seal_value and seal_value not in self.catalog.seals:
                errors.append(f'{area_name}[{index}] invalid seal: {seal_value}')

        if 'ability' in card:
            ability = card['ability']
            for sticker in ('eternal', 'perishable', 'rental'):
                if sticker in ability and not self._is_bool_literal(ability[sticker]):
                    errors.append(f'{area_name}[{index}] {sticker} must be true/false')

        if 'base' not in card:
            errors.append(f'{area_name}[{index}] missing base map')
        else:
            base = card['base']
            is_playing_card = self._is_playing_card(card)

            if area_name == 'jokers' and is_playing_card:
                errors.append(f'{area_name}[{index}] playing_card must be false for Joker area')
            
            if is_playing_card:
                if 'suit' not in base:
                    errors.append(f'{area_name}[{index}] missing base.suit')
                else:
                    suit_value = self._normalize_literal(base['suit'])
                    if suit_value == 'nil':
                        errors.append(f'{area_name}[{index}] base.suit is nil')

                if 'value' not in base:
                    errors.append(f'{area_name}[{index}] missing base.value')
                else:
                    rank_value = self._normalize_literal(base['value'])
                    if rank_value == 'nil':
                        errors.append(f'{area_name}[{index}] base.value is nil')

        if 'pinned' in card and not self._is_bool_literal(card['pinned']):
            errors.append(f'{area_name}[{index}] pinned must be true/false')

        return errors

    @staticmethod
    def _is_contiguous_numeric_keys(cards_map, editor):
        keys = []
        for key, _card in editor._iter_map_entries(cards_map):
            try:
                keys.append(int(str(key)))
            except Exception:
                return False
        if not keys:
            return True
        keys = sorted(keys)
        return keys == list(range(1, len(keys) + 1))

    def validate(self, editor):
        errors = []
        errors.extend(self._validate_core_paths(editor))

        for area_name in ('jokers', 'deck', 'hand', 'consumeables'):
            try:
                cards = editor._card_area_cards(area_name)
            except Exception:
                if area_name in ('jokers', 'deck', 'hand'):
                    errors.append(f'Missing required card area cards map: {area_name}.cards')
                continue

            if not self._is_contiguous_numeric_keys(cards, editor):
                errors.append(f'{area_name} card keys are non-contiguous numeric array keys (must be 1..N)')

            idx = 1
            for _key, card in editor._iter_map_entries(cards):
                errors.extend(self._validate_card_schema(card, area_name, idx))
                idx += 1

        return errors
