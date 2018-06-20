import os
import string
import escapism

# Optionally enable user authentication for selected OAuth providers.

if os.environ.get('OAUTH_SERVICE_TYPE') == 'GitHub':
    from oauthenticator.github import GitHubOAuthenticator
    c.JupyterHub.authenticator_class = GitHubOAuthenticator

elif os.environ.get('OAUTH_SERVICE_TYPE') == 'GitLab':
    from oauthenticator.gitlab import GitLabOAuthenticator
    c.JupyterHub.authenticator_class = GitLabOAuthenticator

c.MyOAuthenticator.oauth_callback_url = os.environ.get('OAUTH_CALLBACK_URL' )
c.MyOAuthenticator.client_id = os.environ.get('OAUTH_CLIENT_ID')
c.MyOAuthenticator.client_secret = os.environ.get('OAUTH_CLIENT_SECRET')

# Provide persistent storage for users notebooks. We share one
# persistent volume for all users, mounting just their subdirectory into
# their pod. The persistent volume type needs to be ReadWriteMany so it
# can be mounted on multiple nodes as can't control where pods for a
# user may land. Because it is a shared volume, there are no quota
# restrictions which prevent a specific user filling up the entire
# persistent volume.
#
# As we need to populate the persistent volume with notebooks from the
# image in an init container, and the command needs to vary based on
# the user, we add the volume mount and init container details using
# the modify_pod_hook. We also need to specify the default_url where
# the browser should start so can land in a subdirectory. For an admin
# user this needs to take into account for fact will be able to see all
# users notebooks.

#c.KubeSpawner.user_storage_pvc_ensure = True
c.KubeSpawner.user_storage_pvc_ensure = False

c.KubeSpawner.pvc_name_template = '%s-notebooks' % c.KubeSpawner.hub_connect_ip

#c.KubeSpawner.user_storage_capacity = '%s' % os.environ['NOTEBOOK_VOLUME_SIZE']

#c.KubeSpawner.user_storage_access_modes = ['ReadWriteMany']

c.KubeSpawner.volumes = [
    {
        'name': 'notebooks',
        'persistentVolumeClaim': {
            'claimName': c.KubeSpawner.pvc_name_template
        }
    }
]

volume_mounts_user = [
    {
        'name': 'notebooks',
        'mountPath': '/opt/app-root/src',
        'subPath': 'notebooks/{username}'
    }
]

volume_mounts_admin = [
    {
        'name': 'notebooks',
        'mountPath': '/opt/app-root/src',
        'subPath': 'notebooks'
    }
]

def interpolate_properties(spawner, template):
    safe_chars = set(string.ascii_lowercase + string.digits)
    username = escapism.escape(spawner.user.name, safe=safe_chars,
            escape_char='-').lower()

    return template.format(
        userid=spawner.user.id,
        username=username
        )

def expand_strings(spawner, src):
    if isinstance(src, list):
        return [expand_strings(spawner, i) for i in src]
    elif isinstance(src, dict):
        return {k: expand_strings(spawner, v) for k, v in src.items()}
    elif isinstance(src, str):
        return interpolate_properties(spawner, src)
    else:
        return src

def modify_pod_hook(spawner, pod):
    if spawner.user.name in spawner.user.authenticator.admin_users:
        volume_mounts = volume_mounts_admin
        workspace = interpolate_properties(spawner, '{username}/workspace')
    else:
        volume_mounts = volume_mounts_user
        workspace = 'workspace'

    pod.spec.containers[0].env.append(dict(name='JUPYTER_MASTER_FILES',
            value='/opt/app-root/master'))
    pod.spec.containers[0].env.append(dict(name='JUPYTER_WORKSPACE_NAME',
            value=workspace))

    pod.spec.containers[0].volume_mounts.extend(
            expand_strings(spawner, volume_mounts))

    return pod

c.KubeSpawner.modify_pod_hook = modify_pod_hook

# Setup culling of idle notebooks if timeout parameter is supplied.

idle_timeout = os.environ.get('JUPYTERHUB_IDLE_TIMEOUT')

if idle_timeout and int(idle_timeout):
    c.JupyterHub.services = [
        {
            'name': 'cull-idle',
            'admin': True,
            'command': ['cull-idle-servers', '--timeout=%s' % idle_timeout],
        }
    ]
