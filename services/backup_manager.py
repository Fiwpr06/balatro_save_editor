import os
import shutil
from datetime import datetime


class BackupManager(object):
    def __init__(self, backup_dir_name='backups', max_backups=30):
        self.backup_dir_name = backup_dir_name
        self.max_backups = max_backups

    def _backup_dir(self, save_path):
        save_dir = os.path.dirname(save_path)
        return os.path.join(save_dir, self.backup_dir_name)

    @staticmethod
    def _parse_backup_index(filename):
        prefix = 'save_backup_'
        suffix = '.jkr'
        if not filename.startswith(prefix) or not filename.endswith(suffix):
            return None
        middle = filename[len(prefix) : -len(suffix)]
        try:
            return int(middle)
        except Exception:
            return None

    def _backup_entries(self, save_path):
        backup_dir = self._backup_dir(save_path)
        if not os.path.isdir(backup_dir):
            return []

        entries = []
        for name in os.listdir(backup_dir):
            index = self._parse_backup_index(name)
            if index is None:
                continue
            full_path = os.path.join(backup_dir, name)
            if not os.path.isfile(full_path):
                continue
            entries.append((index, full_path))
        entries.sort(key=lambda item: item[0], reverse=True)
        return entries

    def create_backup(self, save_path):
        if not os.path.isfile(save_path):
            raise FileNotFoundError(f'Save file not found: {save_path}')

        backup_dir = self._backup_dir(save_path)
        os.makedirs(backup_dir, exist_ok=True)

        entries = self._backup_entries(save_path)
        next_index = (entries[0][0] + 1) if entries else 1
        backup_name = f'save_backup_{next_index}.jkr'
        backup_path = os.path.join(backup_dir, backup_name)

        shutil.copy2(save_path, backup_path)
        self._prune_backups(save_path)
        return backup_path

    def _prune_backups(self, save_path):
        entries = self._backup_entries(save_path)
        if self.max_backups is None or self.max_backups <= 0:
            return

        if len(entries) <= self.max_backups:
            return

        removable = entries[self.max_backups :]
        for _index, path in removable:
            # Always keep at least one backup.
            if len(self._backup_entries(save_path)) <= 1:
                break
            try:
                os.remove(path)
            except Exception:
                continue

    def list_backups(self, save_path):
        data = []
        for index, path in self._backup_entries(save_path):
            try:
                stat = os.stat(path)
                created_at = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec='seconds')
                size = stat.st_size
            except Exception:
                created_at = None
                size = None
            data.append(
                {
                    'index': index,
                    'name': os.path.basename(path),
                    'path': path,
                    'created_at': created_at,
                    'size': size,
                }
            )
        return data

    def latest_backup(self, save_path):
        items = self.list_backups(save_path)
        return items[0] if items else None

    def restore_backup(self, save_path, backup_path=None):
        selected_path = backup_path
        if not selected_path:
            latest = self.latest_backup(save_path)
            if not latest:
                raise FileNotFoundError('No backup exists to restore.')
            selected_path = latest['path']

        if not os.path.isfile(selected_path):
            raise FileNotFoundError(f'Backup not found: {selected_path}')

        with open(selected_path, 'rb') as handle:
            blob = handle.read()
        if not blob:
            raise ValueError('Backup file is empty or corrupted.')

        shutil.copy2(selected_path, save_path)
        return selected_path
