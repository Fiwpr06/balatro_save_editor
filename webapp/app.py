import os
import uuid
import tempfile
from decimal import Decimal, InvalidOperation
from threading import Lock

from flask import Flask, jsonify, render_template, request, send_from_directory, session, send_file

from services.editor_service import EditorService


ALLOWED_AREAS = {'jokers', 'consumeables', 'deck', 'hand'}


class AppState:
    def __init__(self):
        self.lock = Lock()
        self.services = {}

    def set_service(self, uid, service):
        with self.lock:
            self.services[uid] = service

    def get_service(self, uid):
        with self.lock:
            return self.services.get(uid)


state = AppState()


def _ok(data=None, status=200):
    payload = {'success': True}
    if data is not None:
        payload.update(data)
    return jsonify(payload), status


def _error(message, status=400, details=None):
    payload = {'success': False, 'error': message}
    if details:
        payload['details'] = details
    return jsonify(payload), status


def _require_service():
    uid = session.get('uid')
    if not uid:
        return None, _error('No session found. Please upload a save file first.', status=400)
    service = state.get_service(uid)
    if not service:
        return None, _error('Session expired or lost due to server restart. Please upload your save file again.', status=400)
    return service, None


def _required_json(*keys):
    payload = request.get_json(silent=True) or {}
    missing = [key for key in keys if key not in payload]
    if missing:
        return None, _error(f"Missing field(s): {', '.join(missing)}", status=422)
    return payload, None


def _parse_non_negative_int(value, name):
    try:
        parsed = int(value)
    except Exception:
        raise ValueError(f'{name} must be an integer')
    if parsed < 0:
        raise ValueError(f'{name} must be >= 0')
    return parsed


def _parse_positive_int(value, name):
    parsed = _parse_non_negative_int(value, name)
    if parsed <= 0:
        raise ValueError(f'{name} must be > 0')
    return parsed


def _coerce_stat_int(value, name):
    text = str(value).strip()
    if text == '':
        raise ValueError(f'{name} is empty')

    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError, OverflowError):
        raise ValueError(f'{name} is not a valid numeric literal: {text}')


def _parse_area(value):
    if value not in ALLOWED_AREAS:
        raise ValueError(f'Invalid area: {value}. Allowed: {sorted(ALLOWED_AREAS)}')
    return value


def _parse_apply_scope(value):
    scope = value or 'selected'
    if scope not in {'selected', 'same_id', 'all'}:
        raise ValueError('apply_scope must be one of: selected, same_id, all')
    return scope


def _core_resources_root(service=None):
    if service is not None:
        return os.path.join(service.game_catalog.core_path, 'resources')
    repo_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(repo_root, 'Balatro-Core', 'resources')


def _core_root_exists():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    core_root = os.path.join(repo_root, 'Balatro-Core')
    return os.path.isdir(core_root), core_root


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'balatro_super_secret_session_key')

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/collection-editor')
    def collection_editor():
        return render_template('collection_editor.html')

    @app.get('/core-assets/<path:relative_path>')
    def core_assets(relative_path):
        uid = session.get('uid')
        service = state.get_service(uid) if uid else None
        resources_root = os.path.realpath(_core_resources_root(service))
        requested = os.path.realpath(os.path.join(resources_root, relative_path))
        if not requested.startswith(resources_root):
            return _error('Invalid asset path.', status=400)
        if not os.path.exists(requested):
            return _error('Asset not found.', status=404)

        parent = os.path.dirname(requested)
        filename = os.path.basename(requested)
        return send_from_directory(parent, filename)

    @app.get('/api/health')
    def health():
        uid = session.get('uid')
        service = state.get_service(uid) if uid else None
        return _ok(
            {
                'loaded': service is not None,
                'save_path': service.get_save_file_path() if service else None
            }
        )

    @app.post('/api/upload-save')
    def upload_save():
        uploaded = request.files.get('file')
        if not uploaded:
            return _error('No file uploaded.', status=422)

        filename = uploaded.filename or ''
        if not filename.lower().endswith('.jkr'):
            return _error('Invalid file type. Please upload a .jkr save file.', status=422)

        uid = session.get('uid')
        if not uid:
            uid = str(uuid.uuid4())
            session['uid'] = uid

        temp_dir = tempfile.mkdtemp(prefix='balatro-save-')
        save_path = os.path.join(temp_dir, 'save.jkr')

        try:
            core_exists, core_root = _core_root_exists()
            if not core_exists:
                return _error(
                    'Server is missing Balatro core data required to parse saves.',
                    status=500,
                    details=(
                        f'Missing directory: {core_root}. '
                        'Your deploy likely excluded Balatro-Core/ (check .gitignore and repository contents).'
                    ),
                )
            uploaded.save(save_path)
            service = EditorService(save_path)
            state.set_service(uid, service)
            return _ok({'save_path': service.get_save_file_path()})
        except Exception as exc:
            app.logger.exception('Upload save failed')
            return _error('Failed to load uploaded save file.', status=500, details=str(exc))

    @app.get('/api/download-save')
    def download_save():
        service, err = _require_service()
        if err:
            return err
        try:
            service.save()
            return send_file(
                service.get_save_file_path(),
                as_attachment=True,
                download_name='save_modified.jkr',
                mimetype='application/octet-stream',
            )
        except ValueError as exc:
            return _error('Save validation failed.', status=422, details=str(exc))
        except Exception as exc:
            return _error('Failed to build download file.', status=500, details=str(exc))

    @app.get('/api/backups')
    def backups():
        service, err = _require_service()
        if err:
            return err
        try:
            return _ok({'items': service.list_backups()})
        except Exception as exc:
            return _error('Failed to list backups.', status=500, details=str(exc))

    @app.post('/api/undo-last-change')
    def undo_last_change():
        service, err = _require_service()
        if err:
            return err
        try:
            changed = service.undo_last_action()
            if not changed:
                return _error('No in-memory change available to undo.', status=422)
            return _ok({'message': 'Last in-memory change was undone.'})
        except Exception as exc:
            return _error('Failed to undo change.', status=500, details=str(exc))

    @app.post('/api/restore-backup')
    def restore_backup():
        service, err = _require_service()
        if err:
            return err

        payload = request.get_json(silent=True) or {}
        backup_path = payload.get('backup_path')

        try:
            result = service.restore_backup(backup_path=backup_path)
            return _ok(
                {
                    'message': 'Backup restored and editor state reloaded.',
                    'restored_from': result['restored_from'],
                    'safety_backup': result['safety_backup'],
                }
            )
        except FileNotFoundError as exc:
            return _error(str(exc), status=404)
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to restore backup.', status=500, details=str(exc))

    @app.get('/api/dashboard')
    def dashboard():
        service, err = _require_service()
        if err:
            return err
        try:
            data = {
                'money': service.get_current_money(),
                'chips': service.get_current_chips(),
                'multiplier': service.get_value(['GAME', 'hands']),
                'current_round': {
                    'hands_left': service.get_value(['GAME', 'current_round', 'hands_left']),
                    'discards_left': service.get_value(['GAME', 'current_round', 'discards_left']),
                    'reroll_cost': service.get_value(['GAME', 'current_round', 'reroll_cost']),
                },
            }
            return _ok({'dashboard': data})
        except Exception as exc:
            return _error('Failed to fetch dashboard.', status=500, details=str(exc))

    @app.get('/api/state/core')
    def core_state():
        service, err = _require_service()
        if err:
            return err
        try:
            return _ok({'state': service.get_core_state_payload()})
        except Exception as exc:
            return _error('Failed to build state payload.', status=500, details=str(exc))

    @app.get('/api/catalog')
    def catalog():
        service, err = _require_service()
        if err:
            return err
        try:
            return _ok({'catalog': service.get_catalog_payload()})
        except Exception as exc:
            return _error('Failed to load catalog.', status=500, details=str(exc))

    @app.get('/api/assets')
    def assets():
        service, err = _require_service()
        if err:
            return err
        try:
            return _ok({'assets': service.get_assets_payload()})
        except Exception as exc:
            return _error('Failed to load assets.', status=500, details=str(exc))

    @app.get('/api/jokers')
    def list_jokers():
        service, err = _require_service()
        if err:
            return err
        try:
            return _ok({'items': service.list_cards('jokers')})
        except Exception as exc:
            return _error('Failed to load jokers.', status=500, details=str(exc))

    @app.get('/api/cards')
    def list_cards():
        service, err = _require_service()
        if err:
            return err
        area = request.args.get('area', 'deck')
        try:
            area = _parse_area(area)
            return _ok({'area': area, 'items': service.list_cards(area)})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to list cards.', status=500, details=str(exc))

    @app.get('/api/consumeables/catalog')
    def list_consumeable_catalog():
        service, err = _require_service()
        if err:
            return err

        set_name = request.args.get('set')
        try:
            return _ok({'items': service.list_consumeable_catalog(set_name=set_name)})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to load consumable catalog.', status=500, details=str(exc))

    @app.post('/api/consumeables/add')
    def add_consumeable():
        service, err = _require_service()
        if err:
            return err

        payload, err = _required_json('center_id')
        if err:
            return err

        center_id = (payload.get('center_id') or '').strip()
        if not center_id:
            return _error('center_id is required.', status=422)

        try:
            result = service.add_consumeable(center_id)
            item = result.get('new_item') or {}
            display_name = item.get('center_name') or center_id
            return _ok(
                {
                    'new_key': result.get('new_key'),
                    'new_item': item,
                    'message': f'Added consumable: {display_name}.',
                }
            )
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to add consumable.', status=500, details=str(exc))

    @app.get('/api/vouchers')
    def list_vouchers():
        service, err = _require_service()
        if err:
            return err

        try:
            return _ok({'items': service.list_voucher_catalog()})
        except Exception as exc:
            return _error('Failed to load vouchers.', status=500, details=str(exc))

    @app.post('/api/voucher/set')
    def set_voucher():
        service, err = _require_service()
        if err:
            return err

        payload, err = _required_json('voucher_key')
        if err:
            return err

        voucher_key = (payload.get('voucher_key') or '').strip()
        if not voucher_key:
            return _error('voucher_key is required.', status=422)

        enabled_raw = payload.get('enabled', True)
        if isinstance(enabled_raw, bool):
            enabled = enabled_raw
        elif isinstance(enabled_raw, str):
            enabled = enabled_raw.strip().lower() in {'1', 'true', 'yes', 'on'}
        else:
            enabled = bool(enabled_raw)

        try:
            result = service.set_voucher_enabled(voucher_key, enabled=enabled)
            status_text = 'Unlocked' if result['enabled'] else 'Locked'
            return _ok({'item': result, 'message': f"{status_text} voucher: {result['name']}."})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to update voucher.', status=500, details=str(exc))

    @app.post('/api/card/preview')
    def preview_card():
        service, err = _require_service()
        if err:
            return err

        payload = request.get_json(silent=True) or {}
        try:
            area = _parse_area(payload.get('area'))
            card_index = _parse_positive_int(payload.get('card_index'), 'card_index')
            apply_scope = _parse_apply_scope(payload.get('apply_scope'))
            has_edition = 'edition' in payload
            has_seal = 'seal' in payload
            edition = payload.get('edition') if has_edition else None
            seal = payload.get('seal') if has_seal else None
            stickers = payload.get('stickers') or {}

            if not has_edition and not has_seal and not stickers:
                return _ok({'preview': {'scope': apply_scope, 'target_count': 0, 'samples': []}, 'validation_errors': []})

            errors = service.validate_card_modification(area, card_index, edition=edition, seal=seal, stickers=stickers)
            preview = service.get_card_modification_preview_scoped(
                area,
                card_index,
                apply_scope=apply_scope,
                edition=edition,
                seal=seal,
                stickers=stickers,
            )
            return _ok({'preview': preview, 'validation_errors': errors})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Preview failed.', status=500, details=str(exc))

    @app.post('/api/card/apply')
    def apply_card_modifiers():
        service, err = _require_service()
        if err:
            return err

        payload = request.get_json(silent=True) or {}
        try:
            area = _parse_area(payload.get('area'))
            card_index = _parse_positive_int(payload.get('card_index'), 'card_index')
            apply_scope = _parse_apply_scope(payload.get('apply_scope'))
            has_edition = 'edition' in payload
            has_seal = 'seal' in payload
            edition = payload.get('edition') if has_edition else None
            seal = payload.get('seal') if has_seal else None
            stickers = payload.get('stickers') or {}

            if not has_edition and not has_seal and not stickers:
                return _ok({'changed': {'scope': apply_scope, 'target_count': 0, 'changed': 0}})

            errors = service.validate_card_modification(area, card_index, edition=edition, seal=seal, stickers=stickers)
            if errors:
                return _error('Invalid card modification.', status=422, details='\n'.join(errors))

            changed = service.apply_card_modifiers_scoped(
                area,
                card_index,
                apply_scope=apply_scope,
                edition=edition,
                seal=seal,
                stickers=stickers,
            )
            return _ok({'changed': changed})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Apply failed.', status=500, details=str(exc))

    @app.post('/api/card/transform/preview')
    def preview_card_transform():
        service, err = _require_service()
        if err:
            return err

        payload = request.get_json(silent=True) or {}
        try:
            area = _parse_area(payload.get('area'))
            card_index = _parse_positive_int(payload.get('card_index'), 'card_index')
            apply_scope = _parse_apply_scope(payload.get('apply_scope'))
            has_suit = 'suit' in payload
            has_rank = 'rank' in payload
            has_enhancement = 'enhancement' in payload
            suit = payload.get('suit') if has_suit else None
            rank = payload.get('rank') if has_rank else None
            enhancement = payload.get('enhancement') if has_enhancement else None

            if suit == '':
                suit = None
            if rank == '':
                rank = None

            if not has_suit and not has_rank and not has_enhancement:
                return _ok({'preview': {'scope': apply_scope, 'target_count': 0, 'samples': []}})

            preview = service.preview_card_transform_scoped(
                area,
                card_index,
                apply_scope=apply_scope,
                suit=suit,
                rank=rank,
                enhancement=enhancement,
            )
            return _ok({'preview': preview})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Transform preview failed.', status=500, details=str(exc))

    @app.post('/api/card/transform/apply')
    def apply_card_transform():
        service, err = _require_service()
        if err:
            return err

        payload = request.get_json(silent=True) or {}
        try:
            area = _parse_area(payload.get('area'))
            card_index = _parse_positive_int(payload.get('card_index'), 'card_index')
            apply_scope = _parse_apply_scope(payload.get('apply_scope'))
            has_suit = 'suit' in payload
            has_rank = 'rank' in payload
            has_enhancement = 'enhancement' in payload
            suit = payload.get('suit') if has_suit else None
            rank = payload.get('rank') if has_rank else None
            enhancement = payload.get('enhancement') if has_enhancement else None

            if suit == '':
                suit = None
            if rank == '':
                rank = None

            if not has_suit and not has_rank and not has_enhancement:
                return _ok({'changed': {'scope': apply_scope, 'target_count': 0, 'changed': 0}})

            changed = service.apply_card_transform_scoped(
                area,
                card_index,
                apply_scope=apply_scope,
                suit=suit,
                rank=rank,
                enhancement=enhancement,
            )
            return _ok({'changed': changed})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Transform apply failed.', status=500, details=str(exc))

    @app.post('/api/edit-joker')
    def edit_joker():
        service, err = _require_service()
        if err:
            return err

        payload, err = _required_json('card_index')
        if err:
            return err

        try:
            card_index = _parse_positive_int(payload.get('card_index'), 'card_index')
            apply_scope = _parse_apply_scope(payload.get('apply_scope'))
            edition = payload.get('edition')
            seal = payload.get('seal')
            stickers = payload.get('stickers') or {}
            errors = service.validate_card_modification(
                'jokers',
                card_index,
                edition=edition,
                seal=seal,
                stickers=stickers,
            )
            if errors:
                return _error('Invalid joker modification.', status=422, details='\n'.join(errors))
            changed = service.apply_card_modifiers_scoped(
                'jokers',
                card_index,
                apply_scope=apply_scope,
                edition=edition,
                seal=seal,
                stickers=stickers,
            )
            return _ok({'changed': changed})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Apply failed.', status=500, details=str(exc))

    @app.post('/api/add-joker')
    def add_joker():
        service, err = _require_service()
        if err:
            return err

        payload, err = _required_json('center_id')
        if err:
            return err

        center_id = (payload.get('center_id') or '').strip()
        edition = payload.get('edition')
        seal = payload.get('seal')
        stickers = payload.get('stickers') or {}

        if not center_id:
            return _error('center_id is required.', status=422)

        enabled_stickers = {key: bool(value) for key, value in stickers.items() if bool(value)}

        try:
            new_key = service.add_joker(center_id)
            if any([edition is not None, seal is not None, bool(enabled_stickers)]):
                selected = service.find_card_by_key('jokers', new_key)
                if selected:
                    validation = service.validate_card_modification(
                        'jokers',
                        selected['index'],
                        edition=edition,
                        seal=seal,
                        stickers=enabled_stickers,
                    )
                    if validation:
                        return _error('Joker added, but attributes are invalid.', status=422, details='\n'.join(validation))
                    service.apply_card_modifiers(
                        'jokers',
                        selected['index'],
                        edition=edition,
                        seal=seal,
                        stickers=enabled_stickers,
                    )

            added_item = service.find_card_by_key('jokers', new_key)
            return _ok({'new_key': new_key, 'new_item': added_item})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to add joker.', status=500, details=str(exc))

    @app.post('/api/remove-card')
    def remove_card():
        service, err = _require_service()
        if err:
            return err

        payload = request.get_json(silent=True) or {}
        try:
            area = _parse_area(payload.get('area'))
            card_index = _parse_positive_int(payload.get('card_index'), 'card_index')
            removed_key = service.remove_card(area, card_index)
            return _ok({'removed_key': removed_key})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to remove card.', status=500, details=str(exc))

    @app.post('/api/remove-joker')
    def remove_joker():
        service, err = _require_service()
        if err:
            return err

        payload, err = _required_json('card_index')
        if err:
            return err

        try:
            card_index = _parse_positive_int(payload.get('card_index'), 'card_index')
            removed_key = service.remove_card('jokers', card_index)
            return _ok({'removed_key': removed_key})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to remove joker.', status=500, details=str(exc))

    @app.get('/api/stats')
    def stats():
        service, err = _require_service()
        if err:
            return err

        try:
            data = {
                'money': _coerce_stat_int(service.get_current_money(), 'money'),
                'chips': _coerce_stat_int(service.get_current_chips(), 'chips'),
                'interest_cap': _coerce_stat_int(service.get_value(['GAME', 'interest_cap']), 'interest_cap'),
                'reroll_cost': _coerce_stat_int(service.get_value(['GAME', 'current_round', 'reroll_cost']), 'reroll_cost'),
                'hands_left': _coerce_stat_int(service.get_value(['GAME', 'current_round', 'hands_left']), 'hands_left'),
                'discards_left': _coerce_stat_int(service.get_value(['GAME', 'current_round', 'discards_left']), 'discards_left'),
                'hand_size': _coerce_stat_int(service.get_value(['GAME', 'starting_params', 'hand_size']), 'hand_size'),
                'joker_slots': _coerce_stat_int(service.get_value(['GAME', 'starting_params', 'joker_slots']), 'joker_slots'),
                'consumable_slots': _coerce_stat_int(service.get_value(['GAME', 'starting_params', 'consumable_slots']), 'consumable_slots'),
            }
            return _ok({'stats': data})
        except Exception as exc:
            return _error('Failed to read stats.', status=500, details=str(exc))

    @app.post('/api/stats/resources')
    def update_resources():
        service, err = _require_service()
        if err:
            return err

        payload = request.get_json(silent=True) or {}
        try:
            money = _parse_non_negative_int(payload.get('money', 0), 'money')
            chips = _parse_non_negative_int(payload.get('chips', 0), 'chips')
            interest_cap = _parse_non_negative_int(payload.get('interest_cap', 0), 'interest_cap')
            reroll_cost = _parse_non_negative_int(payload.get('reroll_cost', 0), 'reroll_cost')
            hands_left = _parse_non_negative_int(payload.get('hands_left', 0), 'hands_left')
            discards_left = _parse_non_negative_int(payload.get('discards_left', 0), 'discards_left')

            service.set_money(money)
            service.set_chips(chips)
            service.set_interest_cap(interest_cap)
            service.set_reroll_cost(reroll_cost)
            service.set_hands_left(hands_left)
            service.set_discards_left(discards_left)
            return _ok({'message': 'Resources updated.'})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to update resources.', status=500, details=str(exc))

    @app.post('/api/stats/capacities')
    def update_capacities():
        service, err = _require_service()
        if err:
            return err

        payload = request.get_json(silent=True) or {}
        try:
            hand_size = _parse_positive_int(payload.get('hand_size', 1), 'hand_size')
            joker_slots = _parse_positive_int(payload.get('joker_slots', 1), 'joker_slots')
            consumable_slots = _parse_positive_int(payload.get('consumable_slots', 1), 'consumable_slots')

            service.set_hand_size(hand_size)
            service.set_joker_slots(joker_slots)
            service.set_consumable_slots(consumable_slots)
            return _ok({'message': 'Capacities updated.'})
        except ValueError as exc:
            return _error(str(exc), status=422)
        except Exception as exc:
            return _error('Failed to update capacities.', status=500, details=str(exc))

    @app.post('/api/god-mode')
    def god_mode():
        service, err = _require_service()
        if err:
            return err

        payload, err = _required_json('action')
        if err:
            return err

        action = payload.get('action')
        try:
            if action == 'infinite_resources':
                service.god_infinite_everything()
                return _ok({'message': 'Infinite resources applied.'})
            if action == 'all_negative_jokers':
                acted = service.god_all_negative_jokers()
                return _ok({'message': f'Applied negative edition to {acted} jokers.'})
            if action == 'max_hands':
                acted = service.god_max_all_hands()
                return _ok({'message': f'Maxed out {acted} poker hands.'})
            if action == 'free_shop':
                service.god_free_shop()
                return _ok({'message': 'Shop items are now free.'})
            if action == 'guaranteed_rng':
                service.god_guaranteed_rng()
                return _ok({'message': '100% RNG triggers applied.'})
            if action == 'unlock_vouchers':
                acted = service.unlock_all_vouchers()
                return _ok({'message': f'Unlocked {acted} vouchers.'})
            if action == 'add_tarots':
                result = service.god_add_tarots()
                return _ok(
                    {
                        'message': (
                            f"Added {result['added']} Tarot card(s) "
                            f"({result['already_present']} already present)."
                        )
                    }
                )
            if action == 'add_planets':
                result = service.god_add_planets()
                return _ok(
                    {
                        'message': (
                            f"Added {result['added']} Planet card(s) "
                            f"({result['already_present']} already present)."
                        )
                    }
                )
            if action == 'add_spectrals':
                result = service.god_add_spectrals()
                return _ok(
                    {
                        'message': (
                            f"Added {result['added']} Spectral card(s) "
                            f"({result['already_present']} already present)."
                        )
                    }
                )
            if action == 'unlock_everything':
                service.god_unlock_everything()
                return _ok({'message': 'Unlock everything applied.'})
            return _error('Unknown god mode action.', status=422)
        except Exception as exc:
            return _error('God mode operation failed.', status=500, details=str(exc))

    return app
