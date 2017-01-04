# Registering email 

This service registers emails for logins where the IDP does not provide email.

## Prerequisites

### Dataporten application

You need to have the dataporten openid information ready. For development, you can do this yourself. On https://dashboard.dataporten.no/, you will need to register an application. After registering, you will find the Client ID and Secret ID under OAuth credentials.

The important fields are:

#### Redirect URI

This is a url only for contact between the httpd server and dataporten. The domain name has to be the exactly same domain name that are used for the service.

    https://[domain name]/callback

for example:

    https://lifeportal.uio.no/callback

#### Auth providers

Select which providers the portal will use.

#### Permissions

Should be set to:

- E-post
- OpenID Connect
- Profilinfo
- Bruker-ID

#### Administrators

For portals maintained by FT, FT should be added as an administrator.

## Installing

The system run by default as a service on port 5000. We will add a deployment script for adding apache/nginx server and setting up an virtualenv.

This service should be run with a none-privileged user. 

To install a virtualenv with requirements:

    virtualenv .venv
    .venv/bin/pip install -r requirements.txt
    . .venv/bin/activate
    python registeremail.py
    
You are then asked for Dataporten secrets and Database credentials. If not using a postgresql database, you will need to edit config.cfg afterwards.

