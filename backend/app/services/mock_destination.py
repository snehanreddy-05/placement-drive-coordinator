import uuid
import datetime
from typing import List, Dict, Any, Optional

class MockEmployerDestination:
    """
    Simulates an external employer recruitment portal API endpoint.
    Maintains real in-memory/persisted intake records and supports failure simulation modes
    for thorough QA testing of reconciliation rules.
    """
    def __init__(self):
        # drive_id -> dict of submission data
        self._intake_store: Dict[str, Dict[str, Any]] = {}
        # Simulation modes: None or "NORMAL", "WRONG_COUNT", "MISSING_ID", "UNEXPECTED_ID", "DUPLICATE_ID", "FAILURE"
        self.simulation_mode: Optional[str] = None
        self.failure_counter: int = 0

    def submit_roster(
        self,
        drive_id: str,
        student_ids: List[str],
        destination_url: str,
        idempotency_key: str,
        simulation_override: Optional[str] = None
    ) -> Dict[str, Any]:
        mode = simulation_override or self.simulation_mode or "NORMAL"

        if mode == "FAILURE":
            raise RuntimeError("Mock employer endpoint returned HTTP 500: Internal Server Error")

        # Check idempotency: if already submitted with this key, return existing receipt
        if drive_id in self._intake_store:
            existing = self._intake_store[drive_id]
            if existing.get("idempotency_key") == idempotency_key:
                return {
                    "receipt_reference": existing["receipt_reference"],
                    "status": "ACCEPTED_IDEMPOTENT",
                    "submitted_count": len(existing["stored_ids"]),
                    "timestamp": existing["timestamp"]
                }

        receipt_ref = f"RCPT-EMP-{uuid.uuid4().hex[:8].upper()}"
        stored_ids = list(student_ids)

        if mode == "WRONG_COUNT" and len(stored_ids) > 1:
            stored_ids = stored_ids[:-1] # Drop one student
        elif mode == "MISSING_ID" and len(stored_ids) > 0:
            stored_ids = [s for idx, s in enumerate(stored_ids) if idx != 0] # Drop first
        elif mode == "UNEXPECTED_ID":
            stored_ids.append("STU_ROGUE_999") # Inject extraneous student
        elif mode == "DUPLICATE_ID" and len(stored_ids) > 0:
            stored_ids.append(stored_ids[0]) # Duplicate first student

        self._intake_store[drive_id] = {
            "receipt_reference": receipt_ref,
            "drive_id": drive_id,
            "destination_url": destination_url,
            "idempotency_key": idempotency_key,
            "stored_ids": stored_ids,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        return {
            "receipt_reference": receipt_ref,
            "status": "ACCEPTED",
            "submitted_count": len(stored_ids),
            "timestamp": self._intake_store[drive_id]["timestamp"]
        }

    def read_back_records(self, drive_id: str) -> Optional[Dict[str, Any]]:
        """
        Reads back the actual records residing in the employer destination.
        """
        return self._intake_store.get(drive_id)

    def clear(self):
        self._intake_store.clear()
        self.simulation_mode = None

mock_destination_service = MockEmployerDestination()
