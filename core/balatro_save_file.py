import datetime
import os
import re
import shutil
import zlib

from core.token_iterator import TokenIterator


class Struct(object):
    def __init__(self, token_iterator):
        self.token_iterator = token_iterator
        self.structs = []

    def __str__(self):
        return ''.join(map(str, self.structs))


class LiteralStruct(Struct):
    def __init__(self, token_iterator, token):
        super().__init__(token_iterator)
        self.structs.append(token)
        if token in ('"', "'"):
            self.structs.extend(token_iterator.until(token))


class MapKeyStruct(Struct):
    def __init__(self, token_iterator, token):
        super().__init__(token_iterator)
        self.structs.append(LiteralStruct(token_iterator, token))
        token = next(token_iterator)
        while not token == ']':
            self.structs.append(LiteralStruct(token_iterator, token))
            token = next(token_iterator)
        self.structs.append(LiteralStruct(token_iterator, token))
        self.structs.append(LiteralStruct(token_iterator, next(token_iterator)))


class MapValueStruct(Struct):
    def __init__(self, token_iterator, token):
        super().__init__(token_iterator)
        if token == '{':
            self.structs.append(MapStruct(token_iterator, token))
        else:
            self.structs.append(LiteralStruct(token_iterator, token))
        self.structs.append(LiteralStruct(token_iterator, next(token_iterator)))


class MapEntryStruct(Struct):
    def __init__(self, token_iterator, token):
        super().__init__(token_iterator)
        self.structs.append(MapKeyStruct(token_iterator, token))
        self.structs.append(MapValueStruct(token_iterator, next(token_iterator)))

    @property
    def key(self):
        key_text = str(self.structs[0])
        match = re.match(r'^\[\s*(?:"((?:\\.|[^"])*)"|\'((?:\\.|[^\'])*)\'|([^\]]+))\s*\]=$', key_text)
        if not match:
            return key_text
        if match.group(1) is not None:
            return bytes(match.group(1), 'utf-8').decode('unicode_escape')
        if match.group(2) is not None:
            return bytes(match.group(2), 'utf-8').decode('unicode_escape')
        return match.group(3).strip()

    @property
    def value(self):
        return self.structs[1].structs[0]


class MapStruct(Struct):
    def __init__(self, token_iterator, token):
        super().__init__(token_iterator)
        self.structs.append(LiteralStruct(token_iterator, token))
        while True:
            token = next(token_iterator)
            if token == '}':
                self.structs.append(LiteralStruct(token_iterator, token))
                return
            elif token == '[':
                self.structs.append(MapEntryStruct(token_iterator, token))
            else:
                self.structs.append(LiteralStruct(token_iterator, token))
                continue

    def __getitem__(self, key):
        for struct in self.structs:
            if not isinstance(struct, MapEntryStruct):
                continue
            if struct.key == key:
                return struct.value
        raise ValueError('No such key')

    def __setitem__(self, key, value):
        for struct in self.structs:
            if not isinstance(struct, MapEntryStruct):
                continue
            if struct.key == key:
                if not isinstance(struct.value, LiteralStruct):
                    raise ValueError('Can only set values of type LiteralStruct')
                if len(struct.value.structs) == 1:
                    struct.value.structs[0] = value
                elif len(struct.value.structs) == 3 and struct.value.structs[0] == '"' and struct.value.structs[2] == '"':
                    struct.value.structs[1] = value
                return

        encoded_key = str(key).replace('\\', '\\\\').replace('"', '\\"')
        encoded_value = self._encode_lua_literal(value)
        entry_text = f'["{encoded_key}"]={encoded_value},'
        entry_tokens = re.split(r'([\[\]{},="\\\'])', entry_text)
        entry_iterator = TokenIterator(entry_tokens)
        new_entry = MapEntryStruct(entry_iterator, next(entry_iterator))
        self.structs.insert(-1, new_entry)

    @staticmethod
    def _encode_lua_literal(value):
        text = str(value)
        if text in ('true', 'false', 'nil'):
            return text
        if re.fullmatch(r'-?\d+(?:\.\d+)?', text):
            return text
        escaped = text.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'

    def __contains__(self, key):
        for struct in self.structs:
            if not isinstance(struct, MapEntryStruct):
                continue
            if struct.key == key:
                return True
        return False

    def __iter__(self):
        for struct in self.structs:
            if not isinstance(struct, MapEntryStruct):
                continue
            yield struct.value


class BalatroSaveFile(object):
    def __init__(self, save_file_path):
        self.save_file_path = save_file_path
        self.save_file_data = self.read(self.save_file_path)
        text = str(self.decompress(self.save_file_data), encoding='ascii')
        self.structs = self.parse_text_to_structs(text)
        self.validate()

    @staticmethod
    def parse_text_to_structs(text):
        structs = []
        tokens = re.split(r'([\[\]{},="\\\'])', text)
        token_iterator = TokenIterator(tokens)

        structs.append(LiteralStruct(token_iterator, next(token_iterator)))
        structs.append(MapStruct(token_iterator, next(token_iterator)))
        return structs

    def load_from_text(self, text):
        self.structs = self.parse_text_to_structs(text)

    @staticmethod
    def read(save_file_path):
        with open(save_file_path, 'rb') as save_file:
            return save_file.read()

    def create_backup(self):
        now = str(datetime.datetime.now()).replace(' ', 'T').replace(':', '')
        save_file_name = os.path.basename(self.save_file_path)
        save_file_directory = os.path.dirname(self.save_file_path)
        save_file_backup_name = save_file_name + f'{now}.bak'
        save_file_backup_path = os.path.join(save_file_directory, save_file_backup_name)
        shutil.copy(self.save_file_path, save_file_backup_path)

    def write(self, create_backup=True, dry_run=True):
        save_file_data = self.compress(bytes(str(self), 'ascii'))
        if create_backup:
            self.create_backup()
        if not dry_run:
            with open(self.save_file_path, 'wb') as f:
                f.write(save_file_data)

    @staticmethod
    def decompress(save_file_data):
        return zlib.decompress(save_file_data, wbits=-zlib.MAX_WBITS)

    @staticmethod
    def compress(save_file_data):
        compressor = zlib.compressobj(level=1, wbits=-zlib.MAX_WBITS)
        return compressor.compress(save_file_data) + compressor.flush()

    # Performed after initial deserialization - Checks if serialization (with no changes) returns to initial file
    def validate(self):
        if not self.save_file_data == self.compress(bytes(str(self), 'ascii')):
            raise Exception('Decompression and Recompression failed!')

    def __str__(self):
        return ''.join(map(str, self.structs))

    def __getitem__(self, name):
        return self.structs[1][name]
