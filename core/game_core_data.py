import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CenterDef:
    center_id: str
    name: str
    set_name: str
    eternal_compat: bool
    effect: str
    config_defaults: Dict[str, str]
    extra_default: Optional[str] = None
    order: Optional[int] = None
    pos_x: Optional[int] = None
    pos_y: Optional[int] = None
    atlas_name: Optional[str] = None


@dataclass
class EditionDef:
    edition_id: str
    display_name: str
    type_name: str
    extra: str


@dataclass
class AtlasDef:
    name: str
    file_name: str
    px: int
    py: int


@dataclass
class CardDef:
    card_id: str
    name: str
    suit: str
    value: str
    pos_x: int
    pos_y: int


@dataclass
class GameCoreCatalog:
    core_path: str
    centers: Dict[str, CenterDef]
    jokers: Dict[str, CenterDef]
    editions: Dict[str, EditionDef]
    seals: List[str]
    stickers: List[str]
    required_card_fields: List[str]
    atlases: Dict[str, AtlasDef]
    cards: Dict[str, CardDef]
    seal_sprites: Dict[str, Dict[str, object]]
    sticker_sprites: Dict[str, Dict[str, object]]
    texture_scale: int

    @staticmethod
    def _extract_brace_block(text: str, marker: str) -> str:
        start_idx = text.find(marker)
        if start_idx < 0:
            return ''
        brace_start = text.find('{', start_idx)
        if brace_start < 0:
            return ''

        depth = 0
        for idx in range(brace_start, len(text)):
            char = text[idx]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[brace_start : idx + 1]
        return ''

    @staticmethod
    def _iter_top_level_entries(block: str):
        if not block:
            return
        idx = 0
        while idx < len(block):
            match = re.search(r'\s*([A-Za-z0-9_]+)\s*=\s*\{', block[idx:])
            if not match:
                break
            key = match.group(1)
            entry_start = idx + match.start()
            brace_start = idx + match.end() - 1

            depth = 0
            end_idx = brace_start
            for pos in range(brace_start, len(block)):
                char = block[pos]
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end_idx = pos
                        break

            entry_text = block[entry_start : end_idx + 1]
            yield key, entry_text
            idx = end_idx + 1

    @staticmethod
    def _extract_string(entry_text: str, field_name: str) -> Optional[str]:
        patterns = [
            rf'{field_name}\s*=\s*"([^"]+)"',
            rf"{field_name}\s*=\s*'([^']+)'",
        ]
        for pattern in patterns:
            match = re.search(pattern, entry_text)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _extract_bool(entry_text: str, field_name: str, default: bool = False) -> bool:
        match = re.search(rf'{field_name}\s*=\s*(true|false)', entry_text)
        if not match:
            return default
        return match.group(1) == 'true'

    @staticmethod
    def _extract_numeric_as_text(entry_text: str, field_name: str) -> Optional[str]:
        match = re.search(rf'{field_name}\s*=\s*(-?\d+(?:\.\d+)?)', entry_text)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _extract_int(entry_text: str, field_name: str) -> Optional[int]:
        match = re.search(rf'{field_name}\s*=\s*(-?\d+)', entry_text)
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _extract_pos(entry_text: str) -> Optional[Dict[str, int]]:
        match = re.search(r'pos\s*=\s*\{\s*x\s*=\s*(-?\d+)\s*,\s*y\s*=\s*(-?\d+)\s*\}', entry_text)
        if not match:
            return None
        return {'x': int(match.group(1)), 'y': int(match.group(2))}

    @staticmethod
    def _extract_named_brace_block(entry_text: str, field_name: str) -> str:
        marker = f'{field_name}'
        start = entry_text.find(marker)
        if start < 0:
            return ''

        eq_idx = entry_text.find('=', start)
        if eq_idx < 0:
            return ''

        brace_start = entry_text.find('{', eq_idx)
        if brace_start < 0:
            return ''

        depth = 0
        in_quote = None
        escape = False
        for idx in range(brace_start, len(entry_text)):
            char = entry_text[idx]

            if in_quote:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == in_quote:
                    in_quote = None
                continue

            if char in ('"', "'"):
                in_quote = char
                continue

            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return entry_text[brace_start : idx + 1]
        return ''

    @staticmethod
    def _split_top_level_csv(text: str) -> List[str]:
        parts: List[str] = []
        buf: List[str] = []
        depth_brace = 0
        depth_bracket = 0
        depth_paren = 0
        in_quote = None
        escape = False

        for char in text:
            if in_quote:
                buf.append(char)
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == in_quote:
                    in_quote = None
                continue

            if char in ('"', "'"):
                in_quote = char
                buf.append(char)
                continue

            if char == '{':
                depth_brace += 1
            elif char == '}':
                depth_brace -= 1
            elif char == '[':
                depth_bracket += 1
            elif char == ']':
                depth_bracket -= 1
            elif char == '(':
                depth_paren += 1
            elif char == ')':
                depth_paren -= 1

            if char == ',' and depth_brace == 0 and depth_bracket == 0 and depth_paren == 0:
                piece = ''.join(buf).strip()
                if piece:
                    parts.append(piece)
                buf = []
                continue

            buf.append(char)

        tail = ''.join(buf).strip()
        if tail:
            parts.append(tail)
        return parts

    @staticmethod
    def _find_top_level_equal(text: str) -> int:
        depth_brace = 0
        depth_bracket = 0
        depth_paren = 0
        in_quote = None
        escape = False

        for idx, char in enumerate(text):
            if in_quote:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == in_quote:
                    in_quote = None
                continue

            if char in ('"', "'"):
                in_quote = char
                continue

            if char == '{':
                depth_brace += 1
            elif char == '}':
                depth_brace -= 1
            elif char == '[':
                depth_bracket += 1
            elif char == ']':
                depth_bracket -= 1
            elif char == '(':
                depth_paren += 1
            elif char == ')':
                depth_paren -= 1

            if char == '=' and depth_brace == 0 and depth_bracket == 0 and depth_paren == 0:
                return idx
        return -1

    @staticmethod
    def _extract_config_defaults(entry_text: str) -> Dict[str, str]:
        config_block = GameCoreCatalog._extract_named_brace_block(entry_text, 'config')
        if not config_block:
            return {}

        body = config_block[1:-1].strip()
        if not body:
            return {}

        defaults: Dict[str, str] = {}
        for item in GameCoreCatalog._split_top_level_csv(body):
            eq_idx = GameCoreCatalog._find_top_level_equal(item)
            if eq_idx < 0:
                continue
            key = item[:eq_idx].strip()
            value = item[eq_idx + 1 :].strip()
            if not key:
                continue
            defaults[key] = value
        return defaults

    @staticmethod
    def _extract_asset_atlases(game_lua: str) -> Dict[str, AtlasDef]:
        atlases: Dict[str, AtlasDef] = {}
        block = GameCoreCatalog._extract_brace_block(game_lua, 'self.asset_atli =')
        if not block:
            return atlases

        entry_pattern = re.compile(
            r'\{\s*name\s*=\s*["\']([^"\']+)["\']\s*,\s*path\s*=\s*([^,]+),\s*px\s*=\s*(\d+)\s*,\s*py\s*=\s*(\d+)',
            re.MULTILINE,
        )
        for match in entry_pattern.finditer(block):
            name = match.group(1)
            path_expr = match.group(2)
            px = int(match.group(3))
            py = int(match.group(4))
            quoted_parts = re.findall(r'"([^"]+)"|\'([^\']+)\'', path_expr)
            flat_parts = [item[0] or item[1] for item in quoted_parts if (item[0] or item[1])]

            file_name = None
            for part in reversed(flat_parts):
                base = os.path.basename(part.strip())
                if '.' in base:
                    file_name = base
                    break

            if not file_name:
                file_match = re.search(r'([A-Za-z0-9_.\-]+\.[A-Za-z0-9]+)', path_expr)
                if file_match:
                    file_name = file_match.group(1)

            if not file_name:
                continue
            atlases[name] = AtlasDef(name=name, file_name=file_name, px=px, py=py)
        return atlases

    @staticmethod
    def _extract_named_sprites(block: str) -> Dict[str, Dict[str, object]]:
        sprites = {}
        if not block:
            return sprites
        pattern = re.compile(
            r'([A-Za-z0-9_]+)\s*=\s*Sprite\([^\n]*ASSET_ATLAS\["([^"]+)"\][^\{]*\{\s*x\s*=\s*(-?\d+)\s*,\s*y\s*=\s*(-?\d+)\s*\}',
            re.MULTILINE,
        )
        for match in pattern.finditer(block):
            name = match.group(1)
            sprites[name] = {
                'atlas': match.group(2),
                'x': int(match.group(3)),
                'y': int(match.group(4)),
            }
        return sprites

    @staticmethod
    def _extract_sticker_sprites(game_lua: str) -> Dict[str, Dict[str, object]]:
        stickers = {}

        eternal_match = re.search(
            r'self\.shared_sticker_eternal\s*=\s*Sprite\([^\n]*ASSET_ATLAS\["([^"]+)"\][^\{]*\{\s*x\s*=\s*(-?\d+)\s*,\s*y\s*=\s*(-?\d+)\s*\}',
            game_lua,
        )
        if eternal_match:
            stickers['eternal'] = {
                'atlas': eternal_match.group(1),
                'x': int(eternal_match.group(2)),
                'y': int(eternal_match.group(3)),
            }

        shared_block = GameCoreCatalog._extract_brace_block(game_lua, 'self.shared_stickers =')
        shared = GameCoreCatalog._extract_named_sprites(shared_block)
        color_to_sticker = {
            'White': 'perishable',
            'Orange': 'rental',
            'Gold': 'pinned',
        }
        for color_name, sticker_name in color_to_sticker.items():
            if color_name in shared:
                stickers[sticker_name] = shared[color_name]

        return stickers

    @staticmethod
    def _extract_seal_sprites(game_lua: str) -> Dict[str, Dict[str, object]]:
        block = GameCoreCatalog._extract_brace_block(game_lua, 'self.shared_seals =')
        return GameCoreCatalog._extract_named_sprites(block)

    @staticmethod
    def _extract_cards(cards_block: str) -> Dict[str, CardDef]:
        cards: Dict[str, CardDef] = {}
        for card_id, entry_text in GameCoreCatalog._iter_top_level_entries(cards_block):
            pos = GameCoreCatalog._extract_pos(entry_text)
            if not pos:
                continue
            cards[card_id] = CardDef(
                card_id=card_id,
                name=GameCoreCatalog._extract_string(entry_text, 'name') or card_id,
                suit=GameCoreCatalog._extract_string(entry_text, 'suit') or '',
                value=GameCoreCatalog._extract_string(entry_text, 'value') or '',
                pos_x=pos['x'],
                pos_y=pos['y'],
            )
        return cards

    @staticmethod
    def _pick_texture_scale(core_path: str, atlases: Dict[str, AtlasDef]) -> int:
        preferred = [2, 1]
        atlas = atlases.get('Joker')
        if not atlas:
            return 2
        for scale in preferred:
            candidate = os.path.join(core_path, 'resources', 'textures', f'{scale}x', atlas.file_name)
            if os.path.exists(candidate):
                return scale
        return 2

    @staticmethod
    def _read_file(path: str) -> str:
        with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
            return handle.read()

    @classmethod
    def from_core_path(cls, core_path: str):
        game_lua_path = os.path.join(core_path, 'game.lua')
        card_lua_path = os.path.join(core_path, 'card.lua')

        game_lua = cls._read_file(game_lua_path)
        card_lua = cls._read_file(card_lua_path)

        centers_block = cls._extract_brace_block(game_lua, 'self.P_CENTERS =')
        cards_block = cls._extract_brace_block(game_lua, 'self.P_CARDS =')
        seals_block = cls._extract_brace_block(game_lua, 'self.P_SEALS =')
        card_save_block = cls._extract_brace_block(card_lua, 'cardTable =')

        centers: Dict[str, CenterDef] = {}
        jokers: Dict[str, CenterDef] = {}
        editions: Dict[str, EditionDef] = {}
        atlases = cls._extract_asset_atlases(game_lua)
        cards = cls._extract_cards(cards_block)
        sticker_sprites = cls._extract_sticker_sprites(game_lua)
        seal_sprites = cls._extract_seal_sprites(game_lua)

        for center_id, entry_text in cls._iter_top_level_entries(centers_block):
            set_name = cls._extract_string(entry_text, 'set') or ''
            name = cls._extract_string(entry_text, 'name') or center_id
            eternal_compat = cls._extract_bool(entry_text, 'eternal_compat', default=False)
            config_defaults = cls._extract_config_defaults(entry_text)
            center_def = CenterDef(
                center_id=center_id,
                name=name,
                set_name=set_name,
                eternal_compat=eternal_compat,
                effect=cls._extract_string(entry_text, 'effect') or '',
                config_defaults=config_defaults,
                extra_default=config_defaults.get('extra'),
                order=cls._extract_int(entry_text, 'order'),
                pos_x=(cls._extract_pos(entry_text) or {}).get('x'),
                pos_y=(cls._extract_pos(entry_text) or {}).get('y'),
                atlas_name=cls._extract_string(entry_text, 'atlas'),
            )
            centers[center_id] = center_def
            if set_name == 'Joker':
                jokers[center_id] = center_def

            if set_name == 'Edition' and center_id.startswith('e_'):
                edition_type = center_id[2:]
                extra_value = cls._extract_numeric_as_text(entry_text, 'extra') or ''
                editions[edition_type] = EditionDef(
                    edition_id=center_id,
                    display_name=name,
                    type_name=edition_type,
                    extra=extra_value,
                )

        seals: List[str] = []
        for seal_name, _entry_text in cls._iter_top_level_entries(seals_block):
            seals.append(seal_name)

        sticker_candidates = set()
        for sticker_key in ('eternal', 'perishable', 'rental', 'pinned'):
            if re.search(rf'\b{sticker_key}\b', card_lua):
                sticker_candidates.add(sticker_key)
        stickers = sorted(sticker_candidates)

        required_card_fields = []
        for line in card_save_block.splitlines():
            field_match = re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
            if not field_match:
                continue
            field_name = field_match.group(1)
            if field_name == 'save_fields':
                continue
            required_card_fields.append(field_name)
        if 'save_fields' not in required_card_fields:
            required_card_fields.insert(0, 'save_fields')

        return cls(
            core_path=core_path,
            centers=centers,
            jokers=jokers,
            editions=editions,
            seals=seals,
            stickers=stickers,
            required_card_fields=required_card_fields,
            atlases=atlases,
            cards=cards,
            seal_sprites=seal_sprites,
            sticker_sprites=sticker_sprites,
            texture_scale=cls._pick_texture_scale(core_path, atlases),
        )

    @classmethod
    def from_default_root(cls, workspace_root: Optional[str] = None):
        root = workspace_root or os.getcwd()
        core_path = os.path.join(root, 'Balatro-Core')
        return cls.from_core_path(core_path)

    def center_name(self, center_id: Optional[str]) -> str:
        if not center_id:
            return 'Unknown'
        center_def = self.centers.get(center_id)
        if not center_def:
            return center_id
        return center_def.name

    def center_set(self, center_id: Optional[str]) -> Optional[str]:
        if not center_id:
            return None
        center_def = self.centers.get(center_id)
        if not center_def:
            return None
        return center_def.set_name

    @staticmethod
    def _value_to_rank_letter(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
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
    def _suit_to_letter(suit: Optional[str]) -> Optional[str]:
        if suit is None:
            return None
        mapping = {
            'Hearts': 'H',
            'Clubs': 'C',
            'Diamonds': 'D',
            'Spades': 'S',
        }
        return mapping.get(str(suit))

    def _texture_rel_path(self, atlas_name: str) -> Optional[str]:
        atlas = self.atlases.get(atlas_name)
        if not atlas:
            return None
        return f'textures/{self.texture_scale}x/{atlas.file_name}'

    def _atlas_payload(self, atlas_name: str) -> Optional[Dict[str, object]]:
        atlas = self.atlases.get(atlas_name)
        if not atlas:
            return None
        rel_path = self._texture_rel_path(atlas_name)
        if not rel_path:
            return None
        return {
            'name': atlas_name,
            'path': rel_path,
            'px': atlas.px,
            'py': atlas.py,
        }

    def _resolve_center_atlas_name(self, center: CenterDef) -> str:
        # Balatro core aliases Planet/Spectral to Tarot and reads all three from Tarots.png.
        if center.set_name in ('Tarot', 'Planet', 'Spectral') and 'Tarot' in self.atlases:
            return 'Tarot'

        if center.atlas_name and center.atlas_name in self.atlases:
            return center.atlas_name

        if center.set_name in self.atlases:
            return center.set_name

        return 'centers'

    def resolve_card_sprite(self, center_id: Optional[str], card_proto: Optional[str], base_suit: Optional[str], base_value: Optional[str], area_name: Optional[str] = None):
        center_def = self.centers.get(center_id) if center_id else None
        center_set = center_def.set_name if center_def else None
        is_joker_or_consumable = (area_name in ('jokers', 'consumeables')) or (center_set in ('Joker', 'Voucher', 'Tarot', 'Planet', 'Spectral', 'Booster'))

        if is_joker_or_consumable:
            if center_id and center_id in self.centers:
                center = self.centers[center_id]
                if center.pos_x is None or center.pos_y is None:
                    raise ValueError(f"Missing texture mapping for Joker/Consumable center {center_id}")
                atlas_name = self._resolve_center_atlas_name(center)
                atlas = self._atlas_payload(atlas_name)
                if not atlas:
                    raise ValueError(f"Missing atlas {atlas_name} for Joker/Consumable center {center_id}")
                return {
                    'atlas': atlas,
                    'x': center.pos_x,
                    'y': center.pos_y,
                    'source': 'P_CENTERS',
                }
            raise ValueError("Missing center_id for Joker/Consumable")
        else:
            # It's a standard playing card
            if card_proto and card_proto in self.cards:
                card_def = self.cards[card_proto]
                atlas = self._atlas_payload('cards_1')
                if atlas:
                    return {
                        'atlas': atlas,
                        'x': card_def.pos_x,
                        'y': card_def.pos_y,
                        'source': 'P_CARDS',
                    }

            suit_letter = self._suit_to_letter(base_suit)
            rank_letter = self._value_to_rank_letter(base_value)
            if suit_letter and rank_letter:
                card_key = f'{suit_letter}_{rank_letter}'
                card_def = self.cards.get(card_key)
                if card_def:
                    atlas = self._atlas_payload('cards_1')
                    if atlas:
                        return {
                            'atlas': atlas,
                            'x': card_def.pos_x,
                            'y': card_def.pos_y,
                            'source': 'P_CARDS',
                        }
            
            # Allow fallback to center id if card proto is missing but it has a center
            if center_id and center_id in self.centers:
                center = self.centers[center_id]
                if center.set_name == 'Enhanced':
                    atlas = self._atlas_payload('cards_1')
                    fallback_card = self.cards.get('H_2')
                    if not fallback_card and self.cards:
                        fallback_card = next(iter(self.cards.values()))
                    if atlas and fallback_card:
                        return {
                            'atlas': atlas,
                            'x': fallback_card.pos_x,
                            'y': fallback_card.pos_y,
                            'source': 'P_CARDS_FALLBACK',
                        }
                if center.pos_x is None or center.pos_y is None:
                    return None
                atlas_name = self._resolve_center_atlas_name(center)
                atlas = self._atlas_payload(atlas_name)
                if not atlas:
                    return None
                return {
                    'atlas': atlas,
                    'x': center.pos_x,
                    'y': center.pos_y,
                    'source': 'P_CENTERS',
                }
            
            raise ValueError(f"Missing texture mapping for generic card. Proto: {card_proto}, Suit: {base_suit}, Value: {base_value}")

    def get_overlay_payload(self):
        editions = {}
        for edition_type, edition in self.editions.items():
            center = self.centers.get(edition.edition_id)
            if not center or center.pos_x is None or center.pos_y is None:
                continue
            atlas = self._atlas_payload(self._resolve_center_atlas_name(center))
            if not atlas:
                continue
            editions[edition_type] = {
                'atlas': atlas,
                'x': center.pos_x,
                'y': center.pos_y,
            }

        seals = {}
        for seal_name, seal in self.seal_sprites.items():
            atlas = self._atlas_payload(str(seal['atlas']))
            if not atlas:
                continue
            seals[seal_name] = {
                'atlas': atlas,
                'x': int(seal['x']),
                'y': int(seal['y']),
            }

        stickers = {}
        for sticker_name, sticker in self.sticker_sprites.items():
            atlas = self._atlas_payload(str(sticker['atlas']))
            if not atlas:
                continue
            stickers[sticker_name] = {
                'atlas': atlas,
                'x': int(sticker['x']),
                'y': int(sticker['y']),
            }

        enhancements = {}
        for center_id, center in self.centers.items():
            if center.set_name != 'Enhanced':
                continue
            if center.pos_x is None or center.pos_y is None:
                continue
            atlas_name = self._resolve_center_atlas_name(center)
            atlas = self._atlas_payload(atlas_name)
            if not atlas:
                continue
            enhancements[center_id] = {
                'atlas': atlas,
                'x': center.pos_x,
                'y': center.pos_y,
            }

        return {
            'editions': editions,
            'seals': seals,
            'stickers': stickers,
            'enhancements': enhancements,
        }
