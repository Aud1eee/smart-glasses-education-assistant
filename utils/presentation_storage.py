import copy
import json
import os
from datetime import datetime


class PresentationStore:
    def __init__(self, root_dir="data"):
        self.root = root_dir
        self.store_path = os.path.join(self.root, "presentation_companion_store.json")
        self.audio_root = os.path.join(self.root, "presentation_audio")
        os.makedirs(self.root, exist_ok=True)
        os.makedirs(self.audio_root, exist_ok=True)
        self._ensure_store()

    def _empty_store(self):
        return {
            "missions": [],
            "rehearsals": [],
            "updated_at": "",
        }

    def _ensure_store(self):
        if not os.path.exists(self.store_path) or os.stat(self.store_path).st_size < 2:
            self._write_store(self._empty_store())
            return
        try:
            self._read_store()
        except Exception:
            self._write_store(self._empty_store())

    def _read_store(self):
        with open(self.store_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            payload = self._empty_store()
        payload.setdefault("missions", [])
        payload.setdefault("rehearsals", [])
        payload.setdefault("updated_at", "")
        return payload

    def _write_store(self, payload):
        payload = copy.deepcopy(payload or self._empty_store())
        payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
        temp_path = f"{self.store_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.store_path)

    def list_missions(self):
        store = self._read_store()
        missions = copy.deepcopy(store.get("missions", []))
        missions.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return missions

    def get_mission(self, mission_id):
        if not mission_id:
            return None
        for mission in self._read_store().get("missions", []):
            if str(mission.get("mission_id", "")).strip() == str(mission_id).strip():
                return copy.deepcopy(mission)
        return None

    def upsert_mission(self, mission):
        mission_id = str((mission or {}).get("mission_id", "")).strip()
        if not mission_id:
            raise ValueError("mission_id is required.")

        store = self._read_store()
        missions = store.get("missions", [])
        replaced = False
        for index, item in enumerate(missions):
            if str(item.get("mission_id", "")).strip() == mission_id:
                missions[index] = copy.deepcopy(mission)
                replaced = True
                break
        if not replaced:
            missions.append(copy.deepcopy(mission))
        store["missions"] = missions
        self._write_store(store)
        return copy.deepcopy(mission)

    def list_rehearsals(self, mission_id=None):
        rehearsals = copy.deepcopy(self._read_store().get("rehearsals", []))
        if mission_id:
            rehearsals = [
                item
                for item in rehearsals
                if str(item.get("mission_id", "")).strip() == str(mission_id).strip()
            ]
        rehearsals.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return rehearsals

    def get_rehearsal(self, rehearsal_id):
        if not rehearsal_id:
            return None
        for rehearsal in self._read_store().get("rehearsals", []):
            if str(rehearsal.get("rehearsal_id", "")).strip() == str(rehearsal_id).strip():
                return copy.deepcopy(rehearsal)
        return None

    def upsert_rehearsal(self, rehearsal):
        rehearsal_id = str((rehearsal or {}).get("rehearsal_id", "")).strip()
        if not rehearsal_id:
            raise ValueError("rehearsal_id is required.")

        store = self._read_store()
        rehearsals = store.get("rehearsals", [])
        replaced = False
        for index, item in enumerate(rehearsals):
            if str(item.get("rehearsal_id", "")).strip() == rehearsal_id:
                rehearsals[index] = copy.deepcopy(rehearsal)
                replaced = True
                break
        if not replaced:
            rehearsals.append(copy.deepcopy(rehearsal))
        store["rehearsals"] = rehearsals
        self._write_store(store)
        return copy.deepcopy(rehearsal)

    def save_audio_blob(self, rehearsal_id, audio_bytes, filename="", content_type=""):
        if not rehearsal_id or not audio_bytes:
            return {"filename": "", "relative_path": "", "size_bytes": 0}

        safe_ext = self._safe_audio_ext(filename=filename, content_type=content_type)
        safe_name = f"{rehearsal_id}{safe_ext}"
        absolute_path = os.path.join(self.audio_root, safe_name)
        with open(absolute_path, "wb") as handle:
            handle.write(audio_bytes)
        return {
            "filename": safe_name,
            "relative_path": os.path.join("data", "presentation_audio", safe_name).replace("\\", "/"),
            "size_bytes": len(audio_bytes),
        }

    def _safe_audio_ext(self, filename="", content_type=""):
        lowered_name = str(filename or "").strip().lower()
        lowered_type = str(content_type or "").strip().lower()
        mapping = {
            "audio/webm": ".webm",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/mp4": ".m4a",
            "audio/x-m4a": ".m4a",
            "audio/ogg": ".ogg",
        }
        if lowered_type in mapping:
            return mapping[lowered_type]
        for ext in (".webm", ".wav", ".mp3", ".m4a", ".ogg"):
            if lowered_name.endswith(ext):
                return ext
        return ".bin"
