"""Domain models for the employees app extending BaseModel."""

import secrets
import string
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel
from apps.organizations.models import Branch, Department, Designation, Organization, Shift, Team


class EmploymentType(models.TextChoices):
    FULL_TIME = "FULL_TIME", _("Full Time")
    PART_TIME = "PART_TIME", _("Part Time")
    CONTRACT = "CONTRACT", _("Contract")
    INTERN = "INTERN", _("Intern")
    FREELANCE = "FREELANCE", _("Freelance")
    TEMPORARY = "TEMPORARY", _("Temporary")


class EmploymentStatus(models.TextChoices):
    CANDIDATE = "CANDIDATE", _("Candidate")
    OFFER_RELEASED = "OFFER_RELEASED", _("Offer Released")
    JOINED = "JOINED", _("Joined")
    PROBATION = "PROBATION", _("Probation")
    CONFIRMED = "CONFIRMED", _("Confirmed")
    ACTIVE = "ACTIVE", _("Active")
    TRANSFERRED = "TRANSFERRED", _("Transferred")
    PROMOTED = "PROMOTED", _("Promoted")
    ON_LEAVE = "ON_LEAVE", _("On Leave")
    SUSPENDED = "SUSPENDED", _("Suspended")
    RESIGNED = "RESIGNED", _("Resigned")
    NOTICE_PERIOD = "NOTICE_PERIOD", _("Notice Period")
    EXITED = "EXITED", _("Exited")
    ARCHIVED = "ARCHIVED", _("Archived")
    TERMINATED = "TERMINATED", _("Terminated")


class SkillProficiency(models.TextChoices):
    BEGINNER = "BEGINNER", _("Beginner")
    INTERMEDIATE = "INTERMEDIATE", _("Intermediate")
    ADVANCED = "ADVANCED", _("Advanced")
    EXPERT = "EXPERT", _("Expert")


class IdentifierType(models.TextChoices):
    PAN = "PAN", _("PAN Card")
    AADHAAR = "AADHAAR", _("Aadhaar Card")
    SSN = "SSN", _("Social Security Number")
    PASSPORT = "PASSPORT", _("Passport")
    DRIVING_LICENSE = "DRIVING_LICENSE", _("Driving License")
    TAX_ID = "TAX_ID", _("Tax Identification Number")
    OTHER = "OTHER", _("Other Identification")


def generate_employee_id() -> str:
    """Generate a unique 6-character uppercase alphanumeric employee ID (EMP-XXXXXX)."""
    random_str = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"EMP-{random_str}"


class Employee(BaseModel):
    """Core Employee record model linking organization hierarchy and workforce details."""

    employee_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        default=generate_employee_id,
        editable=False,
        help_text=_("Immutable auto-generated unique Employee Code (EMP-XXXXXX)."),
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="employees",
        help_text=_("Associated organization instance."),
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="employees",
        help_text=_("Assigned operational branch location."),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees",
        help_text=_("Assigned organizational department unit."),
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.PROTECT,
        related_name="employees",
        help_text=_("Assigned job designation position."),
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        help_text=_("Assigned team unit."),
    )
    reporting_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
        help_text=_("Direct reporting manager employee record."),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_record",
        help_text=_("Linked authentication user account."),
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        help_text=_("Assigned reusable work shift template."),
    )
    first_name = models.CharField(
        max_length=150,
        help_text=_("Legal given first name."),
    )
    last_name = models.CharField(
        max_length=150,
        help_text=_("Legal surname or last name."),
    )
    display_name = models.CharField(
        max_length=300,
        blank=True,
        help_text=_("Preferred display name for UI views."),
    )
    official_email = models.EmailField(
        max_length=255,
        db_index=True,
        help_text=_("Official enterprise email address."),
    )
    official_phone = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Official corporate phone number."),
    )
    employment_type = models.CharField(
        max_length=50,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME,
        help_text=_("Nature of employment engagement."),
    )
    employment_status = models.CharField(
        max_length=50,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.PROBATION,
        help_text=_("Current lifecycle status of employment."),
    )
    date_of_joining = models.DateField(
        help_text=_("Official starting date of employment."),
    )
    probation_period_months = models.PositiveIntegerField(
        default=3,
        help_text=_("Probationary period duration in months."),
    )
    confirmation_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date of employment confirmation after probation."),
    )
    work_location = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Physical work office location or remote status."),
    )
    photo = models.URLField(
        max_length=500,
        blank=True,
        help_text=_("Profile photo URL."),
    )
    gender = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Gender designation."),
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date of birth."),
    )
    blood_group = models.CharField(
        max_length=10,
        blank=True,
        help_text=_("Blood group specification."),
    )
    nationality = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Citizenship nationality."),
    )
    marital_status = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Marital status."),
    )
    status = models.CharField(
        max_length=50,
        default="ACTIVE",
        help_text=_("Record availability status."),
    )

    class Meta:
        verbose_name = _("employee")
        verbose_name_plural = _("employees")
        ordering = ["first_name", "last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "official_email"],
                name="unique_employee_official_email_per_org",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "official_email"], name="idx_emp_org_email"),
            models.Index(fields=["organization", "employment_status"], name="idx_emp_org_status"),
            models.Index(fields=["department", "designation"], name="idx_emp_dept_desig"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"

    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)


class EmployeeProfile(BaseModel):
    """Detailed personal, contact, address, and identity details for an Employee."""

    employee = models.OneToOneField(
        Employee,
        on_delete=models.PROTECT,
        related_name="profile",
        help_text=_("Associated employee record."),
    )
    personal_email = models.EmailField(
        max_length=255,
        blank=True,
        help_text=_("Personal contact email address."),
    )
    personal_phone = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Personal phone number."),
    )
    current_address = models.TextField(
        blank=True,
        help_text=_("Current residential address."),
    )
    permanent_address = models.TextField(
        blank=True,
        help_text=_("Permanent home address."),
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("City location."),
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("State or province."),
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Country location."),
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("ZIP or postal code."),
    )
    languages = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of spoken/written languages."),
    )
    bio = models.TextField(
        blank=True,
        help_text=_("Professional short biography."),
    )
    linkedin_url = models.URLField(
        max_length=255,
        blank=True,
        help_text=_("LinkedIn profile URL."),
    )
    github_url = models.URLField(
        max_length=255,
        blank=True,
        help_text=_("GitHub profile URL."),
    )
    website_url = models.URLField(
        max_length=255,
        blank=True,
        help_text=_("Personal portfolio website URL."),
    )
    passport_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Passport identification number."),
    )
    driving_license = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Driving license number."),
    )
    pan_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("PAN card number."),
    )
    aadhaar_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Aadhaar national ID number."),
    )
    tax_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Government tax registration ID."),
    )

    class Meta:
        verbose_name = _("employee profile")
        verbose_name_plural = _("employee profiles")

    def __str__(self):
        return f"Profile for {self.employee.employee_id}"


class EmergencyContact(BaseModel):
    """Emergency contacts for an Employee ranked by priority."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
        help_text=_("Associated employee record."),
    )
    name = models.CharField(
        max_length=255,
        help_text=_("Full name of emergency contact."),
    )
    relationship = models.CharField(
        max_length=100,
        help_text=_("Relationship to employee (e.g. Spouse, Parent, Sibling)."),
    )
    phone = models.CharField(
        max_length=50,
        help_text=_("Primary contact phone number."),
    )
    email = models.EmailField(
        max_length=255,
        blank=True,
        help_text=_("Contact email address."),
    )
    address = models.TextField(
        blank=True,
        help_text=_("Contact home address."),
    )
    priority = models.PositiveIntegerField(
        default=1,
        help_text=_("Contact priority rank (1 = Primary, 2 = Secondary)."),
    )

    class Meta:
        verbose_name = _("emergency contact")
        verbose_name_plural = _("emergency contacts")
        ordering = ["priority", "name"]

    def __str__(self):
        return f"{self.name} ({self.relationship}) - {self.employee.employee_id}"


class Education(BaseModel):
    """Academic background and degree credentials of an Employee."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="education_history",
        help_text=_("Associated employee record."),
    )
    institution = models.CharField(
        max_length=255,
        help_text=_("School, college, or university name."),
    )
    degree = models.CharField(
        max_length=150,
        help_text=_("Degree name (e.g. B.Tech, M.Sc, MBA)."),
    )
    specialization = models.CharField(
        max_length=150,
        blank=True,
        help_text=_("Field of study or major specialization."),
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Course start date."),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Course graduation/completion date."),
    )
    grade = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("GPA, percentage, or honors distinction grade."),
    )

    class Meta:
        verbose_name = _("education record")
        verbose_name_plural = _("education records")
        ordering = ["-end_date"]

    def __str__(self):
        return f"{self.degree} from {self.institution} ({self.employee.employee_id})"


class Experience(BaseModel):
    """Prior corporate work history background of an Employee."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="experience_history",
        help_text=_("Associated employee record."),
    )
    company = models.CharField(
        max_length=255,
        help_text=_("Previous employer company name."),
    )
    designation = models.CharField(
        max_length=150,
        help_text=_("Job title/designation held."),
    )
    start_date = models.DateField(
        help_text=_("Employment start date."),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Employment end date."),
    )
    is_current_company = models.BooleanField(
        default=False,
        help_text=_("Flag indicating current active engagement."),
    )
    description = models.TextField(
        blank=True,
        help_text=_("Key responsibilities and achievements description."),
    )

    class Meta:
        verbose_name = _("experience record")
        verbose_name_plural = _("experience records")
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.designation} at {self.company} ({self.employee.employee_id})"


class Skill(BaseModel):
    """Categorized technical and functional skills possessed by an Employee."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="skills",
        help_text=_("Associated employee record."),
    )
    name = models.CharField(
        max_length=100,
        help_text=_("Skill name (e.g. Python, Django, React, Finance)."),
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Skill category (e.g. Backend, Soft Skills, Leadership)."),
    )
    level = models.CharField(
        max_length=50,
        choices=SkillProficiency.choices,
        default=SkillProficiency.INTERMEDIATE,
        help_text=_("Self-assessed proficiency level."),
    )
    years_of_experience = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0.0,
        help_text=_("Years of practical experience with this skill."),
    )

    class Meta:
        verbose_name = _("skill")
        verbose_name_plural = _("skills")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.level}) - {self.employee.employee_id}"


class Certification(BaseModel):
    """Professional certifications and accredited credentials of an Employee."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="certifications",
        help_text=_("Associated employee record."),
    )
    title = models.CharField(
        max_length=255,
        help_text=_("Certification course/title name."),
    )
    provider = models.CharField(
        max_length=255,
        help_text=_("Issuing organization or authority (e.g. AWS, Cisco, PMP)."),
    )
    issue_date = models.DateField(
        help_text=_("Date certificate was awarded."),
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date certificate expires."),
    )
    credential_id = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Unique credential identification code."),
    )
    credential_url = models.URLField(
        max_length=500,
        blank=True,
        help_text=_("URL link to verify credential authenticity."),
    )

    class Meta:
        verbose_name = _("certification")
        verbose_name_plural = _("certifications")
        ordering = ["-issue_date"]

    def __str__(self):
        return f"{self.title} by {self.provider} ({self.employee.employee_id})"


class DocumentReference(BaseModel):
    """Official employee document attachment references and file metadata."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="documents",
        help_text=_("Associated employee record."),
    )
    document_type = models.CharField(
        max_length=100,
        help_text=_("Document category (e.g. RESUME, PASSPORT, OFFER_LETTER)."),
    )
    document_number = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Document identifier number."),
    )
    issue_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Document issuing date."),
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Document expiration date."),
    )
    file_url = models.URLField(
        max_length=500,
        help_text=_("Secure cloud storage URL path to uploaded document file."),
    )
    verification_status = models.CharField(
        max_length=50,
        default="PENDING",
        help_text=_("Document verification status (PENDING, VERIFIED, REJECTED)."),
    )

    class Meta:
        verbose_name = _("document reference")
        verbose_name_plural = _("document references")

    def __str__(self):
        return f"{self.document_type} for {self.employee.employee_id}"


class EmployeeIdentifier(BaseModel):
    """Government and official custom identity documents for an Employee."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="identifiers",
        help_text=_("Associated employee record."),
    )
    identifier_type = models.CharField(
        max_length=50,
        choices=IdentifierType.choices,
        default=IdentifierType.OTHER,
        help_text=_("Identification document type."),
    )
    identifier_number = models.CharField(
        max_length=100,
        help_text=_("Unique identifier document number."),
    )
    issuing_country = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Country of issue."),
    )

    class Meta:
        verbose_name = _("employee identifier")
        verbose_name_plural = _("employee identifiers")

    def __str__(self):
        return f"{self.identifier_type}: {self.identifier_number} ({self.employee.employee_id})"


class EmploymentHistory(BaseModel):
    """Audit log trail tracking Transfers, Promotions, Department, & Manager changes."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="employment_history",
        help_text=_("Associated employee record."),
    )
    change_type = models.CharField(
        max_length=100,
        help_text=_("Mutation category (PROMOTION, TRANSFER, DEPARTMENT_CHANGE, MANAGER_CHANGE)."),
    )
    effective_date = models.DateField(
        help_text=_("Date change takes legal effect."),
    )
    previous_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("JSON snapshot of previous values before mutation."),
    )
    new_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("JSON snapshot of updated values after mutation."),
    )
    remarks = models.TextField(
        blank=True,
        help_text=_("Operational rationale or notes regarding change."),
    )

    class Meta:
        verbose_name = _("employment history")
        verbose_name_plural = _("employment histories")
        ordering = ["-effective_date"]

    def __str__(self):
        return f"[{self.change_type}] {self.employee.employee_id} on {self.effective_date}"


class EmployeeResignation(BaseModel):
    """Resignation lifecycle tracking model for notice period and exit workflows."""

    class ResignationStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending Approval")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        WITHDRAWN = "WITHDRAWN", _("Withdrawn")

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="resignations",
        help_text=_("Associated employee record."),
    )
    resignation_date = models.DateField(
        help_text=_("Date resignation request was formally submitted."),
    )
    notice_period_days = models.PositiveIntegerField(
        default=30,
        help_text=_("Required notice period duration in days."),
    )
    requested_exit_date = models.DateField(
        help_text=_("Employee requested last working day."),
    )
    approved_exit_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("HR/Manager approved last working day."),
    )
    status = models.CharField(
        max_length=50,
        choices=ResignationStatus.choices,
        default=ResignationStatus.PENDING,
        db_index=True,
        help_text=_("Resignation workflow state."),
    )
    reason = models.TextField(
        blank=True,
        help_text=_("Stated reason for resignation."),
    )
    comments = models.TextField(
        blank=True,
        help_text=_("Manager/HR approval or rejection comments."),
    )
    processed_by_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("User UUID of approving/rejecting manager or HR officer."),
    )

    class Meta:
        verbose_name = _("employee resignation")
        verbose_name_plural = _("employee resignations")
        ordering = ["-resignation_date"]

    def __str__(self):
        return f"Resignation: {self.employee.employee_id} ({self.status})"


class EmployeeAuditEvent(BaseModel):
    """Detailed audit log trail for Employee Lifecycle Engine status changes and mutations."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="audit_events",
        help_text=_("Associated employee instance."),
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("Category identifier of the audit event."),
    )
    user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("UUID of the initiating user."),
    )
    user_email = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Email address of the initiating user."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("Client IP address."),
    )
    request_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Correlation request ID."),
    )
    previous_state = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Previous state values snapshot."),
    )
    new_state = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("New state values snapshot."),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional context metadata."),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text=_("Event creation timestamp."),
    )

    class Meta:
        verbose_name = _("employee audit event")
        verbose_name_plural = _("employee audit events")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["employee", "event_type"], name="idx_empaudit_emp_event"),
            models.Index(fields=["employee", "timestamp"], name="idx_empaudit_emp_time"),
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.employee.employee_id} at {self.timestamp}"


class ManagerType(models.TextChoices):
    PRIMARY = "PRIMARY", _("Primary Reporting Manager")
    SECONDARY = "SECONDARY", _("Secondary Reporting Manager")
    FUNCTIONAL = "FUNCTIONAL", _("Functional Manager")
    HR = "HR", _("HR Manager")
    PROJECT = "PROJECT", _("Project Manager")
    MENTOR = "MENTOR", _("Mentor / Advisor")


class AssignmentType(models.TextChoices):
    SHIFT = "SHIFT", _("Shift Template Assignment")
    WORK_LOCATION = "WORK_LOCATION", _("Work Location Assignment")
    TEAM = "TEAM", _("Team Unit Assignment")
    DEPARTMENT = "DEPARTMENT", _("Department Unit Assignment")
    BRANCH = "BRANCH", _("Branch Unit Assignment")
    MANAGER = "MANAGER", _("Reporting Manager Assignment")


class WorkLocationType(models.TextChoices):
    OFFICE = "OFFICE", _("Physical Office Location")
    REMOTE = "REMOTE", _("Full Remote Work")
    HYBRID = "HYBRID", _("Hybrid Work Model")
    SITE = "SITE", _("Client / Field Site")
    REGIONAL = "REGIONAL", _("Regional Territory")


class ManagerAssignment(BaseModel):
    """Multi-type reporting manager assignments for matrix and functional organizations."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="manager_assignments",
        help_text=_("Subordinate employee instance."),
    )
    manager = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="subordinate_assignments",
        help_text=_("Assigned manager employee instance."),
    )
    manager_type = models.CharField(
        max_length=50,
        choices=ManagerType.choices,
        default=ManagerType.PRIMARY,
        db_index=True,
        help_text=_("Role category of manager assignment."),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Flag indicating active assignment."),
    )
    effective_date = models.DateField(
        help_text=_("Effective start date of manager assignment."),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("End date of manager assignment (null if currently active)."),
    )

    class Meta:
        verbose_name = _("manager assignment")
        verbose_name_plural = _("manager assignments")
        ordering = ["-effective_date"]
        indexes = [
            models.Index(fields=["employee", "manager_type", "is_active"], name="idx_mgrassign_emp_type"),
        ]

    def __str__(self):
        return f"{self.manager_type}: {self.manager.display_name} -> {self.employee.display_name}"


class WorkforceAssignment(BaseModel):
    """Immutable audit tracking for Shifts, Work Locations, Teams, Departments, and Branch movements."""

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="workforce_assignments",
        help_text=_("Associated employee instance."),
    )
    assignment_type = models.CharField(
        max_length=50,
        choices=AssignmentType.choices,
        db_index=True,
        help_text=_("Movement/Assignment category."),
    )
    effective_date = models.DateField(
        db_index=True,
        help_text=_("Effective start date."),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Effective end date (null if current active)."),
    )
    is_temporary = models.BooleanField(
        default=False,
        help_text=_("Flag indicating temporary assignment."),
    )
    previous_value = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("JSON snapshot of previous configuration."),
    )
    new_value = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("JSON snapshot of new configuration."),
    )
    reason = models.TextField(
        blank=True,
        help_text=_("Operational rationale notes."),
    )
    actor_user_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("UUID of the user executing the change."),
    )

    class Meta:
        verbose_name = _("workforce assignment")
        verbose_name_plural = _("workforce assignments")
        ordering = ["-effective_date"]
        indexes = [
            models.Index(fields=["employee", "assignment_type"], name="idx_wfassign_emp_type"),
            models.Index(fields=["effective_date", "end_date"], name="idx_wfassign_dates"),
        ]

    def __str__(self):
        return f"[{self.assignment_type}] {self.employee.employee_id} ({self.effective_date})"


