"""
Source registry: the CMS files a release is built from, with their exact headers.

Every header below was read from the live files in September 2026. A build
compares each downloaded file against its expected header before mapping a
single row: a renamed or missing CMS column stops the build with the names
involved, rather than silently loading NULLs.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    local_name: str
    # Provider Data Catalog dataset id (Care Compare) or None for data.cms.gov catalog titles.
    pdc_id: str | None
    header: tuple[str, ...]
    # Chain performance carries a variable tail of quality-measure columns; only the prefix is fixed.
    allow_extra_columns: bool = False
    notes: str = ""


PROVIDER_INFO_HEADER = (
    "CMS Certification Number (CCN)", "Provider Name", "Provider Address", "City/Town", "State", "ZIP Code",
    "Telephone Number", "Provider SSA County Code", "County/Parish", "Urban", "Ownership Type",
    "Number of Certified Beds", "Average Number of Residents per Day", "Average Number of Residents per Day Footnote",
    "Provider Type", "Provider Resides in Hospital", "Legal Business Name",
    "Date First Approved to Provide Medicare and Medicaid Services", "Chain Name", "Chain ID",
    "Number of Facilities in Chain", "Chain Average Overall 5-star Rating", "Chain Average Health Inspection Rating",
    "Chain Average Staffing Rating", "Chain Average QM Rating", "Continuing Care Retirement Community",
    "Special Focus Status", "Abuse Icon", "High Performing Icon", "Most Recent Health Inspection More Than 2 Years Ago",
    "Provider Changed Ownership in Last 12 Months", "With a Resident and Family Council",
    "Automatic Sprinkler Systems in All Required Areas", "Overall Rating", "Overall Rating Footnote",
    "Health Inspection Rating", "Health Inspection Rating Footnote", "QM Rating", "QM Rating Footnote",
    "Long-Stay QM Rating", "Long-Stay QM Rating Footnote", "Short-Stay QM Rating", "Short-Stay QM Rating Footnote",
    "Staffing Rating", "Staffing Rating Footnote", "Reported Staffing Footnote", "Physical Therapist Staffing Footnote",
    "Reported Nurse Aide Staffing Hours per Resident per Day", "Reported LPN Staffing Hours per Resident per Day",
    "Reported RN Staffing Hours per Resident per Day", "Reported Licensed Staffing Hours per Resident per Day",
    "Reported Total Nurse Staffing Hours per Resident per Day",
    "Total number of nurse staff hours per resident per day on the weekend",
    "Registered Nurse hours per resident per day on the weekend",
    "Reported Physical Therapist Staffing Hours per Resident Per Day", "Total nursing staff turnover",
    "Total nursing staff turnover footnote", "Registered Nurse turnover", "Registered Nurse turnover footnote",
    "Number of administrators who have left the nursing home", "Administrator turnover footnote",
    "Nursing Case-Mix Index", "Nursing Case-Mix Index Ratio", "Case-Mix Nurse Aide Staffing Hours per Resident per Day",
    "Case-Mix LPN Staffing Hours per Resident per Day", "Case-Mix RN Staffing Hours per Resident per Day",
    "Case-Mix Total Nurse Staffing Hours per Resident per Day",
    "Case-Mix Weekend Total Nurse Staffing Hours per Resident per Day",
    "Adjusted Nurse Aide Staffing Hours per Resident per Day", "Adjusted LPN Staffing Hours per Resident per Day",
    "Adjusted RN Staffing Hours per Resident per Day", "Adjusted Total Nurse Staffing Hours per Resident per Day",
    "Adjusted Weekend Total Nurse Staffing Hours per Resident per Day", "Rating Cycle 1 Standard Survey Health Date",
    "Rating Cycle 1 Standard Survey Footnote",
    "Rating Cycle 1 Total Number of Health Deficiencies", "Rating Cycle 1 Number of Standard Health Deficiencies",
    "Rating Cycle 1 Number of Complaint Health Deficiencies", "Rating Cycle 1 Health Deficiency Score",
    "Rating Cycle 1 Number of Health Revisits", "Rating Cycle 1 Health Revisit Score", "Rating Cycle 1 Total Health Score",
    "Rating Cycle 2 Standard Health Survey Date", "Rating Cycle 2 Standard Survey Footnote",
    "Rating Cycle 2/3 Total Number of Health Deficiencies",
    "Rating Cycle 2 Number of Standard Health Deficiencies", "Rating Cycle 2/3 Number of Complaint Health Deficiencies",
    "Rating Cycle 2/3 Health Deficiency Score", "Rating Cycle 2/3 Number of Health Revisits",
    "Rating Cycle 2/3 Health Revisit Score", "Rating Cycle 2/3 Total Health Score", "Total Weighted Health Survey Score",
    "Number of Citations from Infection Control Inspections", "Number of Fines", "Total Amount of Fines in Dollars",
    "Number of Payment Denials", "Total Number of Penalties", "Location", "Latitude", "Longitude", "Geocoding Footnote",
    "Processing Date",
)

PENALTIES_HEADER = (
    "CMS Certification Number (CCN)", "Provider Name", "Provider Address", "City/Town", "State", "ZIP Code",
    "Penalty Date", "Penalty Type", "Fine ID", "Fine Amount", "Payment Denial Start Date",
    "Payment Denial Length in Days", "Location", "Processing Date",
)

OWNERSHIP_HEADER = (
    "CMS Certification Number (CCN)", "Provider Name", "Provider Address", "City/Town", "State", "ZIP Code",
    "Role played by Owner or Manager in Facility", "Owner Type", "Owner Name", "Ownership Percentage",
    "Association Date", "Location", "Processing Date",
)

ENROLLMENTS_HEADER = (
    "ENROLLMENT ID", "ENROLLMENT STATE", "PROVIDER TYPE CODE", "PROVIDER TYPE TEXT", "NPI", "MULTIPLE NPI FLAG", "CCN",
    "ASSOCIATE ID", "ORGANIZATION NAME", "DOING BUSINESS AS NAME", "INCORPORATION DATE", "INCORPORATION STATE",
    "ORGANIZATION TYPE STRUCTURE", "ORGANIZATION OTHER TYPE TEXT", "PROPRIETARY_NONPROFIT",
    "NURSING HOME PROVIDER NAME", "AFFILIATION ENTITY NAME", "AFFILIATION ENTITY ID", "ADDRESS LINE 1",
    "ADDRESS LINE 2", "CITY", "STATE", "ZIP CODE",
)

ALL_OWNERS_HEADER = (
    "ENROLLMENT ID", "ASSOCIATE ID", "ORGANIZATION NAME", "ASSOCIATE ID - OWNER", "TYPE - OWNER", "ROLE CODE - OWNER",
    "ROLE TEXT - OWNER", "ASSOCIATION DATE - OWNER", "FIRST NAME - OWNER", "MIDDLE NAME - OWNER", "LAST NAME - OWNER",
    "TITLE - OWNER", "ORGANIZATION NAME - OWNER", "DOING BUSINESS AS NAME - OWNER", "ADDRESS LINE 1 - OWNER",
    "ADDRESS LINE 2 - OWNER", "CITY - OWNER", "STATE - OWNER", "ZIP CODE - OWNER", "PERCENTAGE OWNERSHIP",
    "CREATED FOR ACQUISITION - OWNER", "CORPORATION - OWNER", "LLC - OWNER", "MEDICAL PROVIDER SUPPLIER - OWNER",
    "MANAGEMENT SERVICES COMPANY - OWNER", "MEDICAL STAFFING COMPANY - OWNER", "HOLDING COMPANY - OWNER",
    "INVESTMENT FIRM - OWNER", "FINANCIAL INSTITUTION - OWNER", "CONSULTING FIRM - OWNER", "FOR PROFIT - OWNER",
    "NON PROFIT - OWNER", "PRIVATE EQUITY COMPANY - OWNER", "REIT - OWNER", "CHAIN HOME OFFICE - OWNER",
    "TRUST OR TRUSTEE - OWNER", "OTHER TYPE - OWNER", "OTHER TYPE TEXT - OWNER", "PARENT COMPANY - OWNER",
    "OWNED BY ANOTHER ORG OR IND - OWNER",
)

CHOW_HEADER = (
    "ENROLLMENT ID - BUYER", "ENROLLMENT STATE - BUYER", "PROVIDER TYPE CODE - BUYER", "PROVIDER TYPE TEXT - BUYER",
    "NPI - BUYER", "MULTIPLE NPI FLAG - BUYER", "CCN - BUYER", "ASSOCIATE ID - BUYER", "ORGANIZATION NAME - BUYER",
    "DOING BUSINESS AS NAME - BUYER", "CHOW TYPE CODE", "CHOW TYPE TEXT", "EFFECTIVE DATE", "ENROLLMENT ID - SELLER",
    "ENROLLMENT STATE - SELLER", "PROVIDER TYPE CODE - SELLER", "PROVIDER TYPE TEXT - SELLER", "NPI - SELLER",
    "MULTIPLE NPI FLAG - SELLER", "CCN - SELLER", "ASSOCIATE ID - SELLER", "ORGANIZATION NAME - SELLER",
    "DOING BUSINESS AS NAME - SELLER",
)

CHAIN_HEADER_PREFIX = (
    "Chain", "Chain ID", "Number of facilities", "Number of states and territories with operations",
    "Number of Special Focus Facilities (SFF)", "Number of SFF candidates", "Number of facilities with an abuse icon",
    "Percentage of facilities with an abuse icon", "Percent of facilities classified as for-profit",
    "Percent of facilities classified as non-profit", "Percent of facilities classified as government-owned",
    "Average overall 5-star rating", "Average health inspection rating", "Average staffing rating",
    "Average quality rating", "Average total nurse hours per resident day",
    "Average total weekend nurse hours per resident day", "Average total Registered Nurse hours per resident day",
    "Average total nursing staff turnover percentage", "Average Registered Nurse turnover percentage",
    "Average number of administrators who have left the nursing home", "Total number of fines",
    "Average number of fines", "Total amount of fines in dollars", "Average amount of fines in dollars",
    "Total number of payment denials", "Average number of payment denials",
)

SOURCES: dict[str, Source] = {
    "provider_info": Source(
        key="provider_info", title="Provider Information", local_name="NH_ProviderInfo.csv", pdc_id="4pq5-n9py",
        header=PROVIDER_INFO_HEADER, notes="Care Compare nursing-home provider file; its Processing Date names the release.",
    ),
    "penalties": Source(
        key="penalties", title="Penalties", local_name="NH_Penalties.csv", pdc_id="g6vv-u9sr", header=PENALTIES_HEADER,
        notes="Fines and payment denials over the three-year lookback CMS publishes.",
    ),
    "ownership": Source(
        key="ownership", title="Ownership", local_name="NH_Ownership.csv", pdc_id="y2hd-n93e", header=OWNERSHIP_HEADER,
        notes="Care Compare owner and manager roles per facility.",
    ),
    "enrollments": Source(
        key="enrollments", title="Skilled Nursing Facility Enrollments", local_name="SNF_Enrollments.csv", pdc_id=None,
        header=ENROLLMENTS_HEADER, notes="PECOS enrollment to CCN crosswalk.",
    ),
    "all_owners": Source(
        key="all_owners", title="Skilled Nursing Facility All Owners", local_name="SNF_All_Owners.csv", pdc_id=None,
        header=ALL_OWNERS_HEADER, notes="Every CMS-855A owner, officer and additional disclosable party with disclosure flags.",
    ),
    "chow": Source(
        key="chow", title="Skilled Nursing Facility Change of Ownership", local_name="SNF_CHOW.csv", pdc_id=None,
        header=CHOW_HEADER, notes="Buyer and seller enrollments for each change of ownership.",
    ),
    "chains": Source(
        key="chains", title="Nursing Home Chain Performance Measures", local_name="Chain_Performance.csv", pdc_id=None,
        header=CHAIN_HEADER_PREFIX, allow_extra_columns=True,
        notes="Affiliated-entity performance file; the National row is the reconciliation target.",
    ),
}

DATA_CMS_GOV_CATALOG = "https://data.cms.gov/data.json"
PDC_METASTORE = "https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items/{id}"

# Roles that make a CMS-855A row an owner or controller of the operator, as
# opposed to an additional disclosable party (landlord, lender, vendor).
OWNER_ROLE_CODES = ("34", "35", "85", "86", "38", "39", "43")

# The nurse-staffing minimums of the May 2024 federal rule, rescinded by the
# interim final rule of December 3, 2025 (effective February 2, 2026). Hours per
# resident per day, compared with reported (not case-mix adjusted) staffing.
REPEALED_RN_FLOOR = 0.55
REPEALED_AIDE_FLOOR = 2.45
REPEALED_TOTAL_FLOOR = 3.48

# States and territories with fewer facilities than this get NULL composite
# scores in state_summary; the research page uses the same threshold.
MIN_FACILITIES_FOR_STATE_INDEX = 10
