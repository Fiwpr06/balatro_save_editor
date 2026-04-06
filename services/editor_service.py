import os

from core.balatro_save_editor import BalatroSaveEditor
from core.game_core_data import GameCoreCatalog
from core.save_validator import SaveStructureValidator
from services.backup_manager import BackupManager


class EditorService(object):
    # Service layer that reuses existing BalatroSaveEditor methods without changing core logic.
    _catalog_cache = {}

    def __init__(self, save_file_path):
        self.editor = BalatroSaveEditor(save_file_path)
        self._undo_stack = []
        self.backup_manager = BackupManager()
        workspace_root = os.getcwd()
        if not os.path.isdir(os.path.join(workspace_root, 'Balatro-Core')):
            workspace_root = os.path.dirname(os.path.dirname(__file__))
        if workspace_root not in self._catalog_cache:
            self._catalog_cache[workspace_root] = GameCoreCatalog.from_default_root(workspace_root)
        self.game_catalog = self._catalog_cache[workspace_root]
        self.validator = SaveStructureValidator(self.game_catalog)

    def _snapshot(self):
        self._undo_stack.append(str(self.editor.balatro_save_file))
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)

    def undo_last_action(self):
        if not self._undo_stack:
            return False
        previous_text = self._undo_stack.pop()
        self.editor.balatro_save_file.load_from_text(previous_text)
        return True

    def edit_money(self, new_value):
        self._snapshot()
        self.editor.edit_money(new_value)

    def edit_chips(self):
        self._snapshot()
        self.editor.edit_chips()

    def edit_multipliers(self, new_mult):
        self._snapshot()
        self.editor.edit_multipliers(new_mult)

    def edit_card_abilities(self):
        self._snapshot()
        self.editor.edit_card_abilities()

    def edit_card_limits(self):
        self._snapshot()
        self.editor.edit_card_limits()

    def set_money(self, value):
        self._snapshot()
        self.editor.set_money(value)

    def set_chips(self, value):
        self._snapshot()
        self.editor._set_by_path(['GAME', 'chips'], value)
        self.editor._set_if_present(['GAME', 'chips_text'], value)

    def set_interest_cap(self, value):
        self._snapshot()
        self.editor.set_interest_cap(value)

    def set_joker_slots(self, value):
        self._snapshot()
        self.editor.set_joker_slots(value)

    def set_consumable_slots(self, value):
        self._snapshot()
        self.editor.set_consumable_slots(value)

    def set_hand_size(self, value):
        self._snapshot()
        self.editor.set_hand_size(value)

    def set_hands_left(self, value):
        self._snapshot()
        self.editor.set_hands_left(value)

    def set_discards_left(self, value):
        self._snapshot()
        self.editor.set_discards_left(value)

    def set_reroll_cost(self, value):
        self._snapshot()
        self.editor.set_reroll_cost(value)

    def set_blind_requirement(self, value):
        self._snapshot()
        self.editor.set_blind_requirement(value)

    def get_hand_names(self):
        return self.editor.get_hand_names()

    def set_hand_stat(self, hand_name, stat_name, value):
        self._snapshot()
        self.editor.set_hand_stat(hand_name, stat_name, value)

    def max_all_hands(self):
        self._snapshot()
        return self.editor.max_all_hands()

    def get_card_count(self, area_name):
        return self.editor.get_card_count(area_name)

    def apply_card_edition(self, area_name, edition_name, apply_all=False, card_index=None):
        self._snapshot()
        return self.editor.apply_card_edition(area_name, edition_name, apply_all=apply_all, card_index=card_index)

    def apply_card_seal(self, area_name, seal_name, apply_all=False, card_index=None):
        self._snapshot()
        return self.editor.apply_card_seal(area_name, seal_name, apply_all=apply_all, card_index=card_index)

    def apply_card_sticker(self, area_name, sticker_name, enabled, apply_all=False, card_index=None):
        self._snapshot()
        return self.editor.apply_card_sticker(
            area_name,
            sticker_name,
            enabled,
            apply_all=apply_all,
            card_index=card_index,
        )

    def list_active_vouchers(self):
        return self.editor.list_active_vouchers()

    def list_voucher_keys(self):
        return self.editor.list_voucher_keys()

    def unlock_all_vouchers(self):
        self._snapshot()
        return self.editor.unlock_all_vouchers()

    def set_voucher(self, voucher_key, enabled):
        self._snapshot()
        self.editor.set_voucher(voucher_key, enabled)

    def _is_locked_center(self, center_id, center_def):
        if center_def is None:
            return True
        if center_def.name == 'Locked':
            return True
        center_key = str(center_id or '').strip().lower()
        if center_key.endswith('_locked') or 'undiscovered' in center_key:
            return True
        return False

    def list_voucher_catalog(self):
        active = set(self.list_active_vouchers())
        vouchers = []

        for center_id, center_def in self.game_catalog.centers.items():
            if center_def.set_name != 'Voucher':
                continue
            if self._is_locked_center(center_id, center_def):
                continue

            try:
                render = self.game_catalog.resolve_card_sprite(
                    center_id=center_id,
                    card_proto=None,
                    base_suit=None,
                    base_value=None,
                    area_name='consumeables',
                )
            except Exception:
                render = None

            vouchers.append(
                {
                    'id': center_id,
                    'name': center_def.name,
                    'set': center_def.set_name,
                    'order': center_def.order,
                    'enabled': center_id in active,
                    'render': render,
                }
            )

        vouchers.sort(key=lambda item: ((item['order'] if item['order'] is not None else 9999), item['id']))
        return vouchers

    def set_voucher_enabled(self, voucher_key, enabled=True):
        center_def = self.game_catalog.centers.get(voucher_key)
        if center_def is None or center_def.set_name != 'Voucher':
            raise ValueError(f'Unknown Voucher center: {voucher_key}')
        if self._is_locked_center(voucher_key, center_def):
            raise ValueError(f'Voucher is not available: {voucher_key}')

        self._snapshot()
        self.editor.set_voucher(voucher_key, bool(enabled))

        return {
            'id': voucher_key,
            'name': center_def.name,
            'enabled': bool(enabled),
        }

    def list_consumeable_catalog(self, set_name=None):
        set_lookup = {
            'tarot': 'Tarot',
            'tarots': 'Tarot',
            'planet': 'Planet',
            'planets': 'Planet',
            'spectral': 'Spectral',
            'spectrals': 'Spectral',
        }
        selected_set = None
        if set_name is not None and str(set_name).strip() != '':
            normalized_set = str(set_name).strip().lower()
            if normalized_set.endswith(' cards'):
                normalized_set = normalized_set[:-6].strip()
            selected_set = set_lookup.get(normalized_set)
            if selected_set is None:
                raise ValueError('set must be one of: Tarot/Tarots, Planet/Planets, Spectral/Spectrals')

        allowed_sets = {'Tarot', 'Planet', 'Spectral'}
        entries = []

        for center_id, center_def in self.game_catalog.centers.items():
            if center_def.set_name not in allowed_sets:
                continue
            if selected_set is not None and center_def.set_name != selected_set:
                continue
            if self._is_locked_center(center_id, center_def):
                continue

            try:
                render = self.game_catalog.resolve_card_sprite(
                    center_id=center_id,
                    card_proto=None,
                    base_suit=None,
                    base_value=None,
                    area_name='consumeables',
                )
            except Exception:
                render = None

            entries.append(
                {
                    'id': center_id,
                    'name': center_def.name,
                    'set': center_def.set_name,
                    'order': center_def.order,
                    'render': render,
                }
            )

        entries.sort(
            key=lambda item: (
                {'Tarot': 1, 'Planet': 2, 'Spectral': 3}.get(item['set'], 99),
                item['order'] if item['order'] is not None else 9999,
                item['id'],
            )
        )
        return entries

    def add_consumeable(self, center_id):
        center_def = self.game_catalog.centers.get(center_id)
        if center_def is None:
            raise ValueError(f'Unknown consumable center: {center_id}')
        if center_def.set_name not in {'Tarot', 'Planet', 'Spectral'}:
            raise ValueError(f'Center is not a consumable card: {center_id}')
        if self._is_locked_center(center_id, center_def):
            raise ValueError(f'Consumable is not available: {center_id}')

        self._snapshot()
        self.editor.ensure_required_card_areas()

        current_count = self.editor.get_card_count('consumeables')
        try:
            current_slots = int(self.get_value(['GAME', 'starting_params', 'consumable_slots']))
        except Exception:
            current_slots = 2

        if current_count + 1 > current_slots:
            self.editor.set_consumable_slots(current_count + 1)

        new_key = self.editor.add_consumeable_by_center(
            center_id,
            center_name=center_def.name,
            center_set=center_def.set_name,
            center_effect=center_def.effect,
            consumeable_config=center_def.config_defaults,
        )

        added = self.find_card_by_key('consumeables', new_key)
        if added:
            try:
                _k, card = self.editor._get_card_by_position('consumeables', int(added['index']))
                self.editor.ensure_card_core_fields(card)
                self.editor.ensure_card_schema(card, game_catalog=self.game_catalog)
            except Exception:
                pass

        return {
            'new_key': new_key,
            'new_item': added,
        }

    def set_probability_denominator(self, value):
        self._snapshot()
        self.editor.set_probability_denominator(value)

    def force_100_rng(self):
        self._snapshot()
        self.editor.force_100_rng()

    def set_seed(self, seed_value):
        self._snapshot()
        self.editor.set_seed(seed_value)

    def god_infinite_everything(self):
        self._snapshot()
        self.editor.god_infinite_everything()

    def god_all_negative_jokers(self):
        self._snapshot()
        return self.editor.god_all_negative_jokers()

    def god_max_all_hands(self):
        self._snapshot()
        return self.editor.god_max_all_hands()

    def god_free_shop(self):
        self._snapshot()
        self.editor.god_free_shop()

    def god_guaranteed_rng(self):
        self._snapshot()
        self.editor.god_guaranteed_rng()

    def god_unlock_everything(self):
        self._snapshot()
        self.editor.god_unlock_everything()

    def add_consumeables_by_set(self, set_name):
        self._snapshot()
        self.editor.ensure_required_card_areas()

        normalized_set = str(set_name or '').strip()
        if normalized_set not in {'Tarot', 'Planet', 'Spectral'}:
            raise ValueError('set_name must be one of: Tarot, Planet, Spectral')

        targets = []
        for center_id, center_def in self.game_catalog.centers.items():
            if center_def.set_name != normalized_set:
                continue
            if center_def.name == 'Locked':
                continue
            if 'undiscovered' in center_id or center_id.endswith('_locked'):
                continue
            targets.append(center_def)

        targets.sort(key=lambda center: ((center.order if center.order is not None else 9999), center.center_id))

        existing_center_ids = {
            card.get('center_id')
            for card in self.list_cards('consumeables')
            if card.get('center_id')
        }

        pending = [center for center in targets if center.center_id not in existing_center_ids]

        if not pending:
            return {
                'category': normalized_set,
                'added': 0,
                'already_present': len(targets),
                'target_total': len(targets),
            }

        current_count = self.editor.get_card_count('consumeables')
        required_slots = current_count + len(pending)
        try:
            current_slots = int(self.get_value(['GAME', 'starting_params', 'consumable_slots']))
        except Exception:
            current_slots = 2

        if required_slots > current_slots:
            self.editor.set_consumable_slots(required_slots)

        added = 0
        for center in pending:
            self.editor.add_consumeable_by_center(
                center_id=center.center_id,
                center_name=center.name,
                center_set=center.set_name,
                center_effect=center.effect,
                consumeable_config=center.config_defaults,
            )
            added += 1

        return {
            'category': normalized_set,
            'added': added,
            'already_present': len(targets) - added,
            'target_total': len(targets),
        }

    def god_add_tarots(self):
        return self.add_consumeables_by_set('Tarot')

    def god_add_planets(self):
        return self.add_consumeables_by_set('Planet')

    def god_add_spectrals(self):
        return self.add_consumeables_by_set('Spectral')

    def get_value(self, keys):
        return self.editor.get_literal_value(keys)

    def search_fields(self, query):
        results = []

        def walk_map(map_struct, prefix):
            for struct in map_struct.structs:
                if hasattr(struct, 'key') and hasattr(struct, 'value'):
                    key = struct.key
                    value = struct.value
                    path = f'{prefix}.{key}' if prefix else key
                    if query.lower() in path.lower():
                        results.append(path)
                    if hasattr(value, 'structs') and len(value.structs) > 0 and str(value.structs[0]) == '{':
                        walk_map(value, path)

        walk_map(self.editor.balatro_save_file.structs[1], '')
        return results[:100]

    def save(self):
        backup_path = self.backup_manager.create_backup(self.get_save_file_path())
        self.editor.ensure_all_card_schemas(game_catalog=self.game_catalog)
        errors = self.validate_save()
        if errors:
            error_lines = '\n'.join(f'- {message}' for message in errors[:20])
            raise ValueError(f'Save validation failed:\n{error_lines}')
        self.editor.balatro_save_file.write(create_backup=False, dry_run=False)
        return backup_path

    def list_backups(self):
        return self.backup_manager.list_backups(self.get_save_file_path())

    def restore_backup(self, backup_path=None):
        current_save = self.get_save_file_path()
        safety_backup_path = self.backup_manager.create_backup(current_save)
        restored_from = self.backup_manager.restore_backup(current_save, backup_path=backup_path)
        try:
            self.editor = BalatroSaveEditor(current_save)
        except Exception:
            self.backup_manager.restore_backup(current_save, backup_path=safety_backup_path)
            self.editor = BalatroSaveEditor(current_save)
            raise ValueError('Selected backup is corrupted and was not applied. Original save was restored.')
        self._undo_stack = []
        return {'restored_from': restored_from, 'safety_backup': safety_backup_path}

    def validate_save(self):
        return self.validator.validate(self.editor)

    def get_property_map(self):
        suit_values = sorted({card.suit for card in self.game_catalog.cards.values() if card.suit})

        rank_values = sorted(
            {card.value for card in self.game_catalog.cards.values() if card.value},
            key=lambda value: (
                0 if str(value).isdigit() else 1,
                int(value) if str(value).isdigit() else {'Jack': 11, 'Queen': 12, 'King': 13, 'Ace': 14}.get(str(value), 99),
            ),
        )

        editions = [
            {
                'id': definition.type_name,
                'name': definition.display_name,
            }
            for definition in sorted(self.game_catalog.editions.values(), key=lambda item: item.type_name)
            if definition.type_name != 'base'
        ]

        enhancements = [
            {
                'id': definition.center_id,
                'name': definition.name,
            }
            for definition in sorted(self.game_catalog.centers.values(), key=lambda item: item.name)
            if definition.set_name == 'Enhanced'
        ]

        seals = list(self.game_catalog.seals)

        edition_aliases = {}
        for edition in editions:
            normalized_name = str(edition['name']).strip().lower()
            if normalized_name and normalized_name != edition['id']:
                edition_aliases[normalized_name] = edition['id']

        return {
            'edition': editions,
            'seal': seals,
            'enhancement': enhancements,
            'suit': suit_values,
            'rank': rank_values,
            'edition_aliases': edition_aliases,
            'card_type_rules': {
                'playing_card': ['edition', 'seal', 'enhancement', 'suit', 'rank'],
                'joker': ['edition', 'seal', 'flags'],
                'consumable': ['edition'],
            },
        }

    def get_catalog_payload(self):
        property_map = self.get_property_map()
        observed_stickers = set(self.game_catalog.stickers)
        for area_name in ('jokers', 'deck', 'hand', 'consumeables'):
            try:
                for card in self.editor.list_cards(area_name):
                    for sticker_name in card.get('stickers', {}).keys():
                        observed_stickers.add(sticker_name)
            except Exception:
                continue

        return {
            'editions': [
                {
                    'type': definition.type_name,
                    'name': definition.display_name,
                    'extra': definition.extra,
                }
                for definition in sorted(self.game_catalog.editions.values(), key=lambda item: item.type_name)
                if definition.type_name != 'base'
            ],
            'seals': list(self.game_catalog.seals),
            'stickers': sorted(observed_stickers),
            'jokers': [
                {
                    'id': definition.center_id,
                    'name': definition.name,
                }
                for definition in sorted(self.game_catalog.jokers.values(), key=lambda item: item.name)
            ],
            'enhancements': property_map['enhancement'],
            'suits': property_map['suit'],
            'ranks': property_map['rank'],
            'assets': self.game_catalog.get_overlay_payload(),
            'property_map': property_map,
        }

    def get_assets_payload(self):
        atlas_payload = {}
        for atlas_name, atlas in self.game_catalog.atlases.items():
            atlas_payload[atlas_name] = {
                'path': f'textures/{self.game_catalog.texture_scale}x/{atlas.file_name}',
                'px': atlas.px,
                'py': atlas.py,
            }

        return {
            'texture_scale': self.game_catalog.texture_scale,
            'atlases': atlas_payload,
            'overlays': self.game_catalog.get_overlay_payload(),
        }

    def list_cards(self, area_name):
        cards = self.editor.list_cards(area_name)
        for card in cards:
            center_id = card.get('center_id')
            card['center_name'] = self.game_catalog.center_name(center_id)
            card['center_set'] = self.game_catalog.center_set(center_id)

            card_proto = card.get('card_proto')
            base_suit = card.get('base_suit')
            base_value = card.get('base_value')

            if area_name == 'jokers' or card.get('center_set') == 'Joker':
                card_proto = None
                base_suit = None
                base_value = None

            try:
                card['render'] = self.game_catalog.resolve_card_sprite(
                    center_id=center_id,
                    card_proto=card_proto,
                    base_suit=base_suit,
                    base_value=base_value,
                    area_name=area_name,
                )
            except ValueError as e:
                # Fallback error for missing texture mappings
                card['render'] = None
                card['render_error'] = str(e)
        return cards

    def find_card_by_key(self, area_name, card_key):
        key_text = str(card_key)
        for card in self.list_cards(area_name):
            if str(card.get('key')) == key_text:
                return card
        return None

    def get_card_modification_preview(self, area_name, card_index, edition=None, seal=None, stickers=None):
        return self.editor.get_card_modification_preview(
            area_name,
            card_index,
            edition=edition,
            seal=seal,
            stickers=stickers,
        )

    def apply_card_modifiers(self, area_name, card_index, edition=None, seal=None, stickers=None):
        self._snapshot()
        return self.editor.set_card_modifiers(
            area_name,
            card_index,
            edition=edition,
            seal=seal,
            stickers=stickers,
        )

    def _resolve_target_indexes(self, area_name, card_index, apply_scope='selected'):
        cards = self.list_cards(area_name)
        if card_index < 1 or card_index > len(cards):
            raise ValueError(f'Card index {card_index} is out of range for {area_name}.')

        if apply_scope == 'selected':
            return [card_index]

        if apply_scope == 'all':
            return [card['index'] for card in cards]

        if apply_scope == 'same_id':
            selected = cards[card_index - 1]
            selected_id = self._scope_identity(selected, area_name)
            if not selected_id:
                return [card_index]
            return [
                card['index']
                for card in cards
                if self._scope_identity(card, area_name) == selected_id
            ]

        raise ValueError(f'Invalid apply_scope: {apply_scope}')

    @staticmethod
    def _normalize_edition_value(edition):
        if edition is None:
            return None
        text = str(edition).strip().lower()
        if not text:
            return ''
        aliases = {
            'holographic': 'holo',
        }
        return aliases.get(text, text)

    @staticmethod
    def _normalize_seal_value(seal):
        if seal is None:
            return None
        text = str(seal).strip()
        if not text:
            return ''
        return text.title()

    @staticmethod
    def _scope_identity(card, area_name):
        if area_name in ('deck', 'hand'):
            return card.get('card_proto') or card.get('id')
        if area_name in ('jokers', 'consumeables'):
            return card.get('center_id') or card.get('id')
        return card.get('id')

    @staticmethod
    def _is_playing_card_row(card, area_name):
        if area_name not in ('deck', 'hand', 'consumeables'):
            return False
        if card.get('center_set') == 'Joker':
            return False
        return bool(card.get('card_proto') and card.get('base_suit') and card.get('base_value'))

    @staticmethod
    def _normalize_modifier_inputs(area_name, edition=None, seal=None, stickers=None):
        edition = EditorService._normalize_edition_value(edition)
        seal = EditorService._normalize_seal_value(seal)
        normalized_stickers = stickers or {}
        if area_name != 'jokers':
            normalized_stickers = {}
        return edition, seal, normalized_stickers

    def _resolve_transform_targets(self, area_name, target_indexes, suit=None, rank=None, enhancement=None):
        requires_playing_card = any(field is not None for field in (suit, rank, enhancement))
        if not requires_playing_card:
            return list(target_indexes)

        cards = self.list_cards(area_name)
        by_index = {card['index']: card for card in cards}
        return [
            index
            for index in target_indexes
            if self._is_playing_card_row(by_index.get(index) or {}, area_name)
        ]

    def get_card_modification_preview_scoped(self, area_name, card_index, apply_scope='selected', edition=None, seal=None, stickers=None):
        edition, seal, stickers = self._normalize_modifier_inputs(
            area_name,
            edition=edition,
            seal=seal,
            stickers=stickers,
        )

        target_indexes = self._resolve_target_indexes(area_name, card_index, apply_scope=apply_scope)
        previews = []
        for index in target_indexes[:10]:
            preview = self.editor.get_card_modification_preview(
                area_name,
                index,
                edition=edition,
                seal=seal,
                stickers=stickers,
            )
            previews.append({'index': index, 'preview': preview})

        return {
            'scope': apply_scope,
            'target_count': len(target_indexes),
            'samples': previews,
        }

    def apply_card_modifiers_scoped(self, area_name, card_index, apply_scope='selected', edition=None, seal=None, stickers=None):
        edition, seal, stickers = self._normalize_modifier_inputs(
            area_name,
            edition=edition,
            seal=seal,
            stickers=stickers,
        )

        target_indexes = self._resolve_target_indexes(area_name, card_index, apply_scope=apply_scope)
        self._snapshot()
        changed = 0
        for index in target_indexes:
            changed += self.editor.set_card_modifiers(
                area_name,
                index,
                edition=edition,
                seal=seal,
                stickers=stickers,
            )
            try:
                _k, card = self.editor._get_card_by_position(area_name, index)
                self.editor.ensure_card_schema(card, game_catalog=self.game_catalog)
            except Exception:
                pass
        return {'scope': apply_scope, 'target_count': len(target_indexes), 'changed': changed}

    def validate_card_modification(self, area_name, card_index, edition=None, seal=None, stickers=None):
        errors = []

        edition, seal, stickers = self._normalize_modifier_inputs(
            area_name,
            edition=edition,
            seal=seal,
            stickers=stickers,
        )

        cards = self.list_cards(area_name)
        if card_index < 1 or card_index > len(cards):
            return [f'Card index {card_index} is out of range for {area_name}.']

        if edition not in (None, '') and edition not in self.game_catalog.editions:
            errors.append(f'Invalid edition: {edition}')

        if seal not in (None, '') and seal not in self.game_catalog.seals:
            errors.append(f'Invalid seal: {seal}')

        known_stickers = set(self.get_catalog_payload()['stickers'])
        for sticker_key in (stickers or {}).keys():
            if sticker_key not in known_stickers:
                errors.append(f'Unknown sticker: {sticker_key}')

        return errors

    def _validate_transform_request(self, area_name, suit=None, rank=None, enhancement=None):
        errors = []
        if area_name not in ('deck', 'hand', 'consumeables', 'jokers'):
            errors.append(f'Invalid area: {area_name}')

        if any(field is not None for field in (suit, rank, enhancement)) and area_name not in ('deck', 'hand'):
            errors.append('Suit/rank/enhancement can only be applied in deck or hand areas.')

        if suit is not None:
            valid_suits = {card.suit for card in self.game_catalog.cards.values() if card.suit}
            if suit not in valid_suits:
                errors.append(f'Invalid suit: {suit}')

        if rank is not None:
            valid_ranks = {card.value for card in self.game_catalog.cards.values() if card.value}
            if rank not in valid_ranks:
                errors.append(f'Invalid rank: {rank}')

        if enhancement is not None and str(enhancement).strip() != '':
            center = self.game_catalog.centers.get(enhancement)
            if not center or center.set_name != 'Enhanced':
                errors.append(f'Invalid enhancement center: {enhancement}')

        return errors

    def _transform_preview_item(self, card, suit=None, rank=None, enhancement=None):
        next_suit = suit or card.get('base_suit')
        next_rank = rank or card.get('base_value')
        if enhancement is None:
            next_center = card.get('center_id')
        elif str(enhancement).strip() == '':
            next_center = 'c_base'
        else:
            next_center = enhancement
        next_center_name = self.game_catalog.center_name(next_center)
        return {
            'index': card.get('index'),
            'current': {
                'suit': card.get('base_suit'),
                'rank': card.get('base_value'),
                'center_id': card.get('center_id'),
                'center_name': card.get('center_name'),
            },
            'next': {
                'suit': next_suit,
                'rank': next_rank,
                'center_id': next_center,
                'center_name': next_center_name,
            },
        }

    def preview_card_transform_scoped(self, area_name, card_index, apply_scope='selected', suit=None, rank=None, enhancement=None):
        errors = self._validate_transform_request(area_name, suit=suit, rank=rank, enhancement=enhancement)
        if errors:
            raise ValueError('\n'.join(errors))

        target_indexes = self._resolve_target_indexes(area_name, card_index, apply_scope=apply_scope)
        target_indexes = self._resolve_transform_targets(
            area_name,
            target_indexes,
            suit=suit,
            rank=rank,
            enhancement=enhancement,
        )
        cards = self.list_cards(area_name)
        by_index = {card['index']: card for card in cards}

        samples = []
        for index in target_indexes[:12]:
            card = by_index.get(index)
            if not card:
                continue
            samples.append(self._transform_preview_item(card, suit=suit, rank=rank, enhancement=enhancement))

        return {
            'scope': apply_scope,
            'target_count': len(target_indexes),
            'samples': samples,
        }

    def apply_card_transform_scoped(self, area_name, card_index, apply_scope='selected', suit=None, rank=None, enhancement=None):
        errors = self._validate_transform_request(area_name, suit=suit, rank=rank, enhancement=enhancement)
        if errors:
            raise ValueError('\n'.join(errors))

        target_indexes = self._resolve_target_indexes(area_name, card_index, apply_scope=apply_scope)
        target_indexes = self._resolve_transform_targets(
            area_name,
            target_indexes,
            suit=suit,
            rank=rank,
            enhancement=enhancement,
        )
        clear_enhancement = enhancement is not None and str(enhancement).strip() == ''
        center_def = self.game_catalog.centers.get(enhancement) if enhancement and str(enhancement).strip() else None

        self._snapshot()
        changed = 0
        for index in target_indexes:
            if suit is not None or rank is not None:
                if self.editor.set_card_face(area_name, index, suit=suit, rank=rank):
                    changed += 1
            if clear_enhancement:
                if self.editor.clear_card_enhancement(
                    area_name,
                    index,
                    center_name=self.game_catalog.center_name('c_base'),
                ):
                    changed += 1
            elif enhancement is not None and center_def is not None:
                if self.editor.set_card_enhancement(
                    area_name,
                    index,
                    enhancement,
                    center_name=center_def.name,
                    center_effect=center_def.effect,
                ):
                    changed += 1
            try:
                _k, card = self.editor._get_card_by_position(area_name, index)
                self.editor.ensure_card_schema(card, game_catalog=self.game_catalog)
            except Exception:
                pass

        return {
            'scope': apply_scope,
            'target_count': len(target_indexes),
            'changed': changed,
        }

    def add_joker(self, center_id):
        if center_id not in self.game_catalog.jokers:
            raise ValueError(f'Unknown Joker center: {center_id}')
        center_def = self.game_catalog.jokers[center_id]
        self._snapshot()
        new_key = self.editor.add_joker_by_center(
            center_id,
            center_name=center_def.name,
            center_effect=center_def.effect,
        )
        added = self.find_card_by_key('jokers', new_key)
        if added:
            try:
                _k, card = self.editor._get_card_by_position('jokers', int(added['index']))
                self.editor.ensure_card_core_fields(card)
                self.editor.ensure_card_schema(card, game_catalog=self.game_catalog)

                if center_def.name == 'Credit Card':
                    try:
                        current = int(float(str(self.editor._get_by_path(['GAME', 'bankrupt_at']))))
                    except Exception:
                        current = None
                    if current is not None:
                        extra_value = 0
                        try:
                            if 'ability' in card and 'extra' in card['ability']:
                                extra_value = int(float(self.editor._parse_literal(card['ability']['extra'])))
                        except Exception:
                            extra_value = 0
                        self.editor._set_by_path(['GAME', 'bankrupt_at'], current - extra_value)
            except Exception:
                pass
        return new_key

    def remove_card(self, area_name, card_index):
        self._snapshot()
        cards_map = self.editor._card_area_cards(area_name)
        target_key = None
        current_index = 1

        for key, _card in self.editor._iter_map_entries(cards_map):
            if current_index == card_index:
                target_key = key
                break
            current_index += 1

        if target_key is None:
            raise ValueError(f'Card index {card_index} is out of range for {area_name}.')

        for struct in list(cards_map.structs):
            if hasattr(struct, 'key') and struct.key == target_key:
                cards_map.structs.remove(struct)
                self.editor._reindex_card_area(area_name)
                return target_key

        raise ValueError(f'Failed to remove card index {card_index} in {area_name}.')

    def get_core_state_payload(self):
        def safe(keys, fallback=None):
            try:
                return self.get_value(keys)
            except Exception:
                return fallback

        hand_rows = []
        try:
            hands = self.editor.balatro_save_file['GAME']['hands']
            for hand_name, hand_value in self.editor._iter_map_entries(hands):
                hand_rows.append(
                    {
                        'name': hand_name,
                        'level': str(hand_value['level']) if 'level' in hand_value else None,
                        'chips': str(hand_value['chips']) if 'chips' in hand_value else None,
                        'mult': str(hand_value['mult']) if 'mult' in hand_value else None,
                    }
                )
        except Exception:
            hand_rows = []

        return {
            'GAME': {
                'modifiers': safe(['GAME', 'modifiers']),
                'current_round': {
                    'hands_left': safe(['GAME', 'current_round', 'hands_left']),
                    'discards_left': safe(['GAME', 'current_round', 'discards_left']),
                    'reroll_cost': safe(['GAME', 'current_round', 'reroll_cost']),
                },
                'hands': hand_rows,
                'probabilities': {
                    'normal': safe(['GAME', 'probabilities', 'normal']),
                },
                'used_vouchers': self.list_active_vouchers(),
            },
            'cardAreas': {
                'jokers': self.list_cards('jokers'),
                'consumeables': self.list_cards('consumeables'),
                'deck': self.list_cards('deck'),
                'hand': self.list_cards('hand'),
            },
        }

    def get_save_file_path(self):
        return self.editor.balatro_save_file.save_file_path

    def get_current_money(self):
        return str(self.editor.balatro_save_file['GAME']['dollars'])

    def get_current_chips(self):
        return str(self.editor.balatro_save_file['GAME']['chips'])
