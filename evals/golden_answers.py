"""
Golden expected outputs for the 12 standard Locust IT helpdesk queries.

These are used by ContextualPrecisionMetric (are relevant chunks ranked first?)
and ContextualRecallMetric (does retrieved context cover all needed info?).

Each golden answer is a concise ideal response — not a transcript, but a summary
of the key resolution steps a correct response should contain.
"""

GOLDEN_ANSWERS: dict[str, str] = {
    "My VPN keeps disconnecting every few minutes": (
        "Update the VPN client to the latest version. Check firewall and antivirus settings "
        "that may be blocking persistent VPN connections. Try switching to a different VPN "
        "server or protocol (e.g. TCP instead of UDP). Review VPN client logs for timeout "
        "or certificate errors. If on a home router, disable any VPN passthrough restrictions."
    ),
    "I forgot my password and cannot log in to my account": (
        "Use the self-service password reset portal at the company intranet. Verify identity "
        "via registered MFA device or backup email. If MFA device is unavailable, contact "
        "the IT helpdesk with your employee ID and manager confirmation for manual reset. "
        "After reset, log in and immediately update password in all linked applications."
    ),
    "My laptop screen is flickering and has black bars": (
        "Update the display driver via Device Manager or the laptop manufacturer's website. "
        "Check and reseat the display cable if accessible. Connect an external monitor to "
        "determine whether the fault is hardware (panel/cable) or software (driver). "
        "If hardware fault is confirmed, raise a hardware repair or replacement request "
        "via the IT Asset Management portal."
    ),
    "I need to install Microsoft Teams on my new laptop": (
        "Download Microsoft Teams from the Company Software Portal — no admin rights are "
        "required for the current version. Alternatively download directly from Microsoft. "
        "Sign in with your corporate email address and password. "
        "If Teams is not available on the Software Portal, raise a software request ticket."
    ),
    "Cannot connect to the company Wi-Fi network": (
        "Forget the Wi-Fi network on your device and reconnect using your corporate credentials. "
        "Ensure the device is enrolled in MDM (check with IT if unsure). "
        "If MAC address filtering is enabled, IT may need to whitelist your device. "
        "Check if you are within range of a Wi-Fi access point and restart the device's "
        "network adapter. Contact the network team if the issue persists."
    ),
    "My email inbox is not syncing on Outlook": (
        "Check the Outlook connection status bar at the bottom — it should show 'Connected'. "
        "Run the Outlook Repair tool via Control Panel > Mail > Repair. "
        "Verify your mailbox size is within the allowed quota. "
        "Re-enter your account credentials if prompted. "
        "Check the IT status page for any known Exchange server issues. "
        "As a last resort, recreate the Outlook profile."
    ),
    "How do I reset my MFA authenticator after getting a new phone?": (
        "Contact the IT helpdesk with your employee ID and manager's email for approval. "
        "IT will reset your MFA registration in the identity management system. "
        "You will receive an email with a re-enrollment link. "
        "Open the link on your new phone, install the authenticator app, and scan the QR code. "
        "Verify the setup with a test login before the old device is fully decommissioned."
    ),
    "The printer on floor 3 is showing offline status": (
        "Check the printer's power and network cable connections. "
        "Restart the Print Spooler service on affected machines: "
        "run services.msc, find Print Spooler, stop and restart it. "
        "Remove and re-add the printer via Settings > Printers & Scanners. "
        "If the printer itself is unresponsive, power-cycle it and verify its IP address "
        "has not changed. Contact the network team if the printer has lost its static IP."
    ),
    "I need admin rights to install a software approved by my manager": (
        "Submit a Privileged Access Request (PAR) via the IT Service Portal. "
        "Attach your manager's written approval email as evidence. "
        "IT will either grant temporary elevated rights (typically 2-hour window) "
        "or arrange for a remote installation session. "
        "Do not use personal admin credentials or request persistent admin rights "
        "outside the PAR process — this is a security policy violation."
    ),
    "My computer is extremely slow and freezing frequently": (
        "Run Windows Disk Cleanup and delete temporary files. "
        "Open Task Manager and check for high CPU, RAM, or disk usage — identify the "
        "resource-heavy process. "
        "Run a full malware scan using the company-approved antivirus. "
        "Disable unnecessary startup programs via Task Manager > Startup tab. "
        "If RAM usage is consistently above 90%, request a RAM upgrade. "
        "If the hard drive is near-full or showing errors, raise a hardware refresh request."
    ),
    "VPN certificate error when connecting from home": (
        "Verify your system date and time are correct — certificate errors are often caused "
        "by clock drift. "
        "Update the VPN client to the latest version from the IT portal. "
        "Download and reinstall the VPN root certificate from the IT intranet certificate page. "
        "Clear the VPN client's certificate cache and credential store. "
        "If using split-tunnel VPN, confirm the routing configuration has not changed. "
        "Contact IT if the certificate has expired — this requires IT to renew it."
    ),
    "I need to request a new hardware laptop, my current one is broken": (
        "Submit a Hardware Refresh Request via the IT Asset Management portal. "
        "Include the asset tag of the broken laptop, a brief fault description, "
        "and your manager's approval reference. "
        "IT will assess whether repair or replacement is appropriate based on device age and fault. "
        "Replacement typically arrives within 3–5 business days. "
        "Back up critical data immediately if the device is still partially functional."
    ),
}
