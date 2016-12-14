import authomatic.core as core
from authomatic.providers import oauth2

__all__ = ['OAuth2', 'Amazon', 'Behance', 'Bitly', 'Cosm', 'Dataporten', 'DeviantART',
           'Eventbrite', 'Facebook', 'Foursquare', 'GitHub', 'Google',
           'LinkedIn', 'PayPal', 'Reddit', 'Viadeo', 'VK', 'WindowsLive',
'Yammer', 'Yandex']

class Dataporten(oauth2.OAuth2):
    """
    Dataporten |oauth2| provider.
    * Dashboard: https://dashboard.dataporten.no/
    * Docs: https://docs.dataporten.no/docs/gettingstarted/
    * API reference:
    Supported :class:`.User` properties:
    * id
    * name
    * email
    * picture
    Unsupported :class:`.User` properties:
    * link
    * username
    * birth_date
    * city
    * country
    * first_name
    * gender
    * last_name
    * locale
    * nickname
    * phone
    * postal_code
    * timezone
    """

    user_authorization_url = 'https://auth.dataporten.no/oauth/authorization'
    access_token_url = 'https://auth.dataporten.no/oauth/token'
    user_info_url = 'https://auth.dataporten.no/openid/userinfo'

    User_info_scope = ['openid', 'profile', 'email']

    # openid yields sub, connect-userid_sec, name
    # profile yields picture
    # email yields email and email_verfied

    supported_user_attributes = core.SupportedUserAttributes(
        id=True,
        email=True,
        name=True,
        picture=True
    )

    def __init__(self, *args, **kwargs):
        super(Dataporten, self).__init__(*args, **kwargs)

    def _x_scope_parser(self, scope):
        # Dataporten has space-separated scopes
        return ' '.join(scope)

    @staticmethod
    def _x_user_parser(user, data):
        user.id = data.get('sub')
        user.name = data.get('name')
        user.email = data.get('email')
        user.picture = data.get('picture')

        return user