import io
import re
from typing import List, Dict, Any, Tuple
import pandas as pd
from app.models.student import Student

REQUIRED_FIELDS = ["student_id", "full_name", "email", "branch", "cgpa", "active_backlogs", "consent_given"]

COLUMN_ALIASES = {
    "student_id": ["student_id", "studentid", "roll_no", "rollno", "id", "student id"],
    "full_name": ["full_name", "fullname", "name", "student_name", "student name"],
    "email": ["email", "email_id", "email address", "mail"],
    "branch": ["branch", "department", "dept", "stream", "major"],
    "cgpa": ["cgpa", "gpa", "score", "grade point"],
    "active_backlogs": ["active_backlogs", "backlogs", "current_backlogs", "arrears", "active backlogs"],
    "consent_given": ["consent_given", "consent", "opt_in", "placement_consent", "consent given"]
}

def normalize_column_name(col: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', str(col).lower())
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if cleaned == re.sub(r'[^a-zA-Z0-9]', '', alias):
                return canonical
    return str(col).strip().lower()

def parse_roster_file(content: bytes, filename: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parses CSV or Excel file, normalizes columns, validates rows, detects duplicates,
    and returns (valid_rows, invalid_rows, summary).
    """
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise ValueError("Unsupported file format. Please upload CSV or XLSX.")
    except Exception as e:
        raise ValueError(f"Failed to read file: {str(e)}")

    # Normalize column names
    col_mapping = {col: normalize_column_name(col) for col in df.columns}
    df = df.rename(columns=col_mapping)

    valid_rows: List[Dict[str, Any]] = []
    invalid_rows: List[Dict[str, Any]] = []
    seen_student_ids = set()

    for idx, row in df.iterrows():
        row_num = idx + 2 # Header is line 1
        errors = []

        # Check required fields presence
        for rf in REQUIRED_FIELDS:
            if rf not in df.columns:
                errors.append(f"Missing required column: {rf}")

        if errors:
            invalid_rows.append({"row_number": row_num, "data": row.to_dict(), "errors": errors})
            continue

        # Extract values
        raw_id = row.get("student_id")
        raw_name = row.get("full_name")
        raw_email = row.get("email")
        raw_branch = row.get("branch")
        raw_cgpa = row.get("cgpa")
        raw_backlogs = row.get("active_backlogs")
        raw_consent = row.get("consent_given")

        # 1. Validate student_id
        if pd.isna(raw_id) or str(raw_id).strip() == "":
            errors.append("Student ID is required and cannot be empty.")
        else:
            stu_id = str(raw_id).strip().upper()
            if stu_id in seen_student_ids:
                errors.append(f"Duplicate student ID detected in file: {stu_id}")
            else:
                seen_student_ids.add(stu_id)

        # 2. Validate full_name
        if pd.isna(raw_name) or str(raw_name).strip() == "":
            errors.append("Student full name is required.")
        else:
            name = str(raw_name).strip()

        # 3. Validate email
        if pd.isna(raw_email) or "@" not in str(raw_email):
            errors.append("Invalid or missing email address.")
        else:
            email = str(raw_email).strip().lower()

        # 4. Validate branch
        if pd.isna(raw_branch) or str(raw_branch).strip() == "":
            errors.append("Branch is required.")
        else:
            branch = str(raw_branch).strip().upper()

        # 5. Validate CGPA
        cgpa_val = None
        try:
            if pd.isna(raw_cgpa):
                errors.append("CGPA is missing.")
            else:
                cgpa_val = float(raw_cgpa)
                if cgpa_val < 0.0 or cgpa_val > 10.0:
                    errors.append(f"CGPA {cgpa_val} out of valid range (0.0 to 10.0).")
        except (ValueError, TypeError):
            errors.append(f"Malformed CGPA value: {raw_cgpa}")

        # 6. Validate backlogs
        backlogs_val = 0
        try:
            if pd.isna(raw_backlogs):
                errors.append("Active backlogs count is missing.")
            else:
                backlogs_val = int(raw_backlogs)
                if backlogs_val < 0:
                    errors.append("Active backlogs count cannot be negative.")
        except (ValueError, TypeError):
            errors.append(f"Malformed active backlogs value: {raw_backlogs}")

        # 7. Validate consent
        consent_val = False
        if pd.isna(raw_consent):
            errors.append("Consent status is missing.")
        else:
            val_str = str(raw_consent).strip().lower()
            if val_str in ["true", "1", "yes", "y", "consented"]:
                consent_val = True
            elif val_str in ["false", "0", "no", "n"]:
                consent_val = False
            else:
                errors.append(f"Unrecognized consent value: {raw_consent}")

        if errors:
            invalid_rows.append({
                "row_number": row_num,
                "data": {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()},
                "errors": errors
            })
        else:
            valid_rows.append({
                "student_id": stu_id,
                "full_name": name,
                "email": email,
                "branch": branch,
                "cgpa": cgpa_val,
                "active_backlogs": backlogs_val,
                "consent_given": consent_val
            })

    summary = {
        "filename": filename,
        "total_rows": len(df),
        "valid_rows_count": len(valid_rows),
        "invalid_rows_count": len(invalid_rows),
        "duplicate_ids_in_file": len(df) - len(seen_student_ids) if len(df) > len(seen_student_ids) else 0
    }

    return valid_rows, invalid_rows, summary
