import requests
import json
import time
import jwt
import argparse
from dotmap import DotMap

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-payload", help="JSON Payload")
    return parser.parse_args()

class IMSJWTTokenExchange:
    def __init__(self, host):
        # check for ims end point
        if not host:
            raise Exception('Client lib must have a target host defined, imsHost or jilHost')
        self.host = host

    def exchangeJwt(self, options):
        checkRequired(options, "issuer")
        checkRequired(options, "subject")
        checkRequired(options, "expiration_time_seconds")
        checkRequired(options, "metascope")
        checkRequired(options, "client_id")
        checkRequired(options, "client_secret")
        checkRequired(options, "privateKey")

        data = DotMap(options)
        jwt_payload = {
            "iss" : data.issuer,
            "sub" : data.subject,
            "exp" : data.expiration_time_seconds,
            "aud" : f'https://{self.host}/c/{data.client_id}'
        }

        for v in data.metascope:
            jwt_payload[f'https://{self.host}/s/{v}'] = True

        jwt_token = jwt.encode(jwt_payload, data.privateKey, algorithm='RS256')

        body = {
            "client_id" : data.client_id,
            "client_secret" : data.client_secret,
            "jwt_token" : jwt_token
        }

        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        response = requests.post(f'https://{self.host}/ims/exchange/jwt', headers=headers, data=body)

        if response.status_code == 200:
            return response.json()['access_token']

        raise Exception('Failed to exchange jwt.')

def checkRequired(options, key):
    if not key in options:
        raise Exception(f'{key} is a required option.')


def assertPresent(data, path, missing):
    if not data:
        missing.append(path)


def exchange(payload):
    try:
        with open(payload) as config:
            integrationConfig = json.load(config)
            data = DotMap(integrationConfig)
            jwtExchange = IMSJWTTokenExchange(data.integration.imsEndpoint)

            missing = []
            assertPresent(data.integration.org, "integration.org", missing)
            assertPresent(data.integration.id, "integration.id", missing)
            assertPresent(data.integration.technicalAccount.clientId, "integration.technicalAccount.clientId", missing)
            assertPresent(data.integration.technicalAccount.clientSecret, "integration.technicalAccount.clientSecret", missing)
            assertPresent(data.integration.metascopes, "integration.metascopes", missing)
            assertPresent(data.integration.privateKey, "integration.privateKey", missing)

            if missing:
                raise Exception("The following configuration elements are missing " + ', '.join(missing))

            current_sec_time = int(round(time.time()))
            expiry_time = current_sec_time + (60*60*24)

            payload = {
                "issuer" : data.integration.org,
                "subject" : data.integration.id,
                "expiration_time_seconds" : expiry_time,
                "metascope" : data.integration.metascopes.split(','),
                "client_id" : data.integration.technicalAccount.clientId,
                "client_secret" : data.integration.technicalAccount.clientSecret,
                "privateKey" : data.integration.privateKey
            }
            return jwtExchange.exchangeJwt(payload)


    except FileNotFoundError:
        print("File not found!")
    except json.decoder.JSONDecodeError:
        print("There was a problem accessing file content! Check again...")

def main(args):
    return print(exchange(args.payload))


if __name__ == "__main__":
    main(parse_args())
