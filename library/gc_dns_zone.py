#!/usr/bin/python

try:
    from libcloud.dns.types import (Provider as DNSProvider, ZoneDoesNotExistError, RecordDoesNotExistError)
    from libcloud.dns.providers import get_driver
    _ = DNSProvider.GOOGLE
    HAS_LIBCLOUD = True
except ImportError:
    HAS_LIBCLOUD = False


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(default='present', choices=['present', 'absent']),
            domain=dict(required=True),
            name=dict(),
            ttl=dict(type='int', default=86400),
            description=dict(),
            service_account_email=dict(),
            pem_file=dict(),
            credentials_file=dict(),
            project_id=dict()
        )
    )
    if not HAS_LIBCLOUD:
        module.fail_json(msg='libcloud with GCE support (0.17.0+) required for this module')

    dns_driver = gc_dns_connect(module)

    state = module.params.get('state')
    zone_domain = module.params.get('domain')
    zone_name = module.params.get('name')
    zone_ttl = module.params.get('ttl')
    zone_description = module.params.get('description')

    if not zone_domain.endswith('.'):
        zone_domain += '.'

    matching_zones = (z for z in dns_driver.iterate_zones() if z.domain == zone_domain)
    zone = next(matching_zones, None)

    changed = False
    if state == 'present' and not zone:
        zone = dns_driver.create_zone(zone_domain, ttl=zone_ttl,
                                      extra={'name': zone_name, 'description': zone_description})
        changed = True
    elif state == 'present' and zone:
        # update zone not supported by Google
        changed = False
    elif state == 'absent' and zone:
        dns_driver.delete_zone(zone)
        changed = True

    results = {
        'changed': changed,
        'zone': {
            'id': zone.id,
            'domain': zone.domain,
            'type': zone.type,
            'ttl': zone.ttl,
            'extra': zone.extra
        }
    }

    module.exit_json(**results)


USER_AGENT_PRODUCT = 'Ansible-gce'
USER_AGENT_VERSION = 'v1'


# copied from ansible.module_utils.gce and changed to reference DNS instead of Compute
def gc_dns_connect(module):
    """Return a Google Cloud DNS connection."""
    service_account_email = module.params.get('service_account_email', None)
    pem_file = module.params.get('pem_file', None)
    project_id = module.params.get('project_id', None)

    # If any of the values are not given as parameters, check the appropriate
    # environment variables.
    if not service_account_email:
        service_account_email = os.environ.get('GCE_EMAIL', None)
    if not project_id:
        project_id = os.environ.get('GCE_PROJECT', None)
    if not pem_file:
        pem_file = os.environ.get('GCE_PEM_FILE_PATH', None)

    # If we still don't have one or more of our credentials, attempt to
    # get the remaining values from the libcloud secrets file.
    if service_account_email is None or pem_file is None:
        try:
            import secrets
        except ImportError:
            secrets = None

        if hasattr(secrets, 'GCE_PARAMS'):
            if not service_account_email:
                service_account_email = secrets.GCE_PARAMS[0]
            if not pem_file:
                pem_file = secrets.GCE_PARAMS[1]
        keyword_params = getattr(secrets, 'GCE_KEYWORD_PARAMS', {})
        if not project_id:
            project_id = keyword_params.get('project', None)

    # If we *still* don't have the credentials we need, then it's time to
    # just fail out.
    if service_account_email is None or pem_file is None or project_id is None:
        module.fail_json(msg='Missing GCE connection parameters in libcloud '
                             'secrets file.')
        return None

    try:
        gc_dns = get_driver(DNSProvider.GOOGLE)(service_account_email, pem_file,
                                   datacenter=module.params.get('zone', None),
                                   project=project_id)
        gc_dns.connection.user_agent_append("%s/%s" % (
            USER_AGENT_PRODUCT, USER_AGENT_VERSION))
    except (RuntimeError, ValueError), e:
        module.fail_json(msg=str(e), changed=False)
    except Exception, e:
        module.fail_json(msg=unexpected_error_msg(e), changed=False)

    return gc_dns


def unexpected_error_msg(error):
    """Create an error string based on passed in error."""
    return 'Unexpected response: (%s). Detail: %s' % (str(error), traceback.format_exc(error))


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()