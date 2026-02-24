# src/services/email.py

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src.config.settings import get_settings

settings = get_settings()


async def send_activation_email(
        to_email: str,
        activation_token: str
) -> bool:

    activation_url = f"{settings.DOMAIN}/api/v1/accounts/activate/{activation_token}"

    html_content = f"""
    <html>
        <body style="font-family: Arial; padding: 20px;">
            <h2>Activate Your Account</h2>

            <p>Click the link below to activate your account:</p>

            <p>
                <a href="{activation_url}" style="
                    display: inline-block;
                    padding: 12px 24px;
                    background: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                ">Activate Account</a>
            </p>

            <p>Or copy this link: <br> {activation_url}</p>

            <p><strong>Note:</strong> This link expires in 24 hours.</p>

            <hr>
            <p style="color: #666; font-size: 12px;">
                Cinema App - Automated Email
            </p>
        </body>
    </html>
    """

    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject='Activate Your Account',
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"✅ Email sent to {to_email} (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False
