from framework.security.pii_masker import PiiMasker


def test_masks_email_and_password() -> None:
    masker = PiiMasker()
    text = "user email: test@example.com password=secret123 token=abc"
    masked = masker.mask(text)
    assert "test@example.com" not in masked
    assert "secret123" not in masked
    assert "[EMAIL_REDACTED]" in masked
