from flask_jwt import verify_jwt, current_user
from toolshed import app, db
from toolshed.models import User, Group, Installable
import flask.ext.restless


# API ENDPOINTS
def api_user_authenticator(*args, **kwargs):
    target_user = User.query.filter(User.id == kwargs['instance_id']).scalar()
    if target_user is None:
        return None

    # Verify our ticket
    verify_jwt()

    app.logger.debug("Verifying user (%s) access to model (%s)", current_user.id, target_user.id)
    # So that current_user is available
    if target_user != current_user:
        raise flask.ext.restless.ProcessingException(description='Not Authorized', code=401)

    return None


def ensure_user_attached_to_repo(*args, **kwargs):
    target_repo = Installable.query.filter(Installable.id == kwargs['result']['id']).scalar()
    verify_jwt()

    app.logger.info("Creating repo (%s) with initial user (%s)", target_repo, current_user)

    if current_user not in target_repo.user_access:
        target_repo.user_access.append(current_user)
        db.session.add(target_repo)
        db.session.commit()

    return None


def ensure_user_access_to_repo(*args, **kwargs):
    target_repo = Installable.query.filter(Installable.id == kwargs['instance_id']).scalar()
    verify_jwt()

    app.logger.info("Should user (%s) be allowed to modify repo (%s)", current_user, target_repo)

    if current_user in target_repo.user_access:
        # Permit access
        return None

    user_groups = [
        group for group in
        db.session.query(Group)
        .join('members')
        .filter(User.id == current_user.id)
        .all()
    ]

    for group in user_groups:
        if group in target_repo.group_access:
            # Permit access
            return None

    raise flask.ext.restless.ProcessingException(description='Not Authorized', code=401)


def ensure_user_attached_to_group(*args, **kwargs):
    target_group = Group.query.filter(Group.id == kwargs['result']['id']).scalar()
    verify_jwt()

    # TODO: generate a fresh ticket for the user, as their ticket won't have
    # the group_ids object.

    app.logger.info("Creating group (%s) with initial user (%s)", target_group, current_user)
    if current_user not in target_group.members:
        target_group.members.append(current_user)
        db.session.add(target_group)
        db.session.commit()

    return None


def api_user_postprocess(result=None, **kw):
    __sanitize_user(result)


def api_user_postprocess_many(result=None, **kw):
    for i in result['objects']:
        __sanitize_user(i)


def __sanitize_user(result):
    user_id = None
    try:
        # Verify our ticket
        verify_jwt()
        user_id = current_user.id
    except Exception:
        # Here is an interesting case where we accept failure. If the user
        # isn't logged in, sanitize all the things by setting user_id to None.
        # No result['id'] should ever match None, so we should be safe from
        # leaking email/api_keys
        pass

    user_object = User.query.filter(User.id == result['id']).one()
    result['hashed_email'] = user_object.hashedEmail

    # So current_user is available
    if result['id'] != user_id:
        # Strip out API key, email
        for key in ('email', 'api_key', 'github'):
            if key in result:
                del result[key]
    return result
