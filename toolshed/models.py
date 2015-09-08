from toolshed import db
import hashlib


# Schema
INSTALLABLE_TYPES = ('package', 'tool', 'datatype', 'suite', 'viz', 'gie')
tags = db.Table(
    'tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id')),
    db.Column('installable_id', db.Integer, db.ForeignKey('installable.id')),
)
members = db.Table(
    'members',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
)
suite_rr = db.Table(
    'suiterevision_revision',
    db.Column('suiterevision_id', db.Integer, db.ForeignKey('suite_revision.id')),
    db.Column('revision_id', db.Integer, db.ForeignKey('revision.id')),
)

installable_user_access = db.Table(
    'installable_user_access',
    db.Column('installable_id', db.Integer, db.ForeignKey('installable.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
)
installable_group_access = db.Table(
    'installable_group_access',
    db.Column('installable_id', db.Integer, db.ForeignKey('installable.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
)
revision_adj = db.Table(
    'revision_adjacency',
    db.Column('from_revision_id', db.Integer, db.ForeignKey('revision.id'), primary_key=True),
    db.Column('to_revision_id', db.Integer, db.ForeignKey('revision.id'), primary_key=True),
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False)
    api_key = db.Column(db.String(32), unique=True)

    email = db.Column(db.String(120), unique=True, nullable=False)
    gpg_pubkey_id = db.Column(db.String(16))

    github = db.Column(db.String(32), unique=True)
    github_username = db.Column(db.String(64))
    github_repos_url = db.Column(db.String(128))

    @property
    def hashedEmail(self):
        return hashlib.md5(self.email).hexdigest()

    def __repr__(self):
        return '<User %s: %s>' % (self.id, self.display_name)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False, unique=True)

    description = db.Column(db.String(), nullable=False)
    website = db.Column(db.String())
    gpg_pubkey_id = db.Column(db.String(16))

    members = db.relationship(
        'User', secondary=members,
        backref=db.backref('group', lazy='dynamic')
    )

    def __repr__(self):
        return '<Group %s: %s>' % (self.id, self.display_name)


class Installable(db.Model):
    id = db.Column('id', db.Integer, primary_key=True)
    # TODO: prevent renaming
    name = db.Column(db.String(120), nullable=False)
    synopsis = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False)

    remote_repository_url = db.Column(db.String())
    homepage_url = db.Column(db.String())

    repository_type = db.Column(db.Enum(*INSTALLABLE_TYPES), nullable=False)

    tags = db.relationship(
        'Tag', secondary=tags,
        backref=db.backref('installable', lazy='dynamic')
    )

    # Installable User Access
    user_access = db.relation(
        'User', secondary=installable_user_access,
        backref=db.backref('installable', lazy='dynamic')
    )
    group_access = db.relation(
        'Group', secondary=installable_group_access,
        backref=db.backref('installable', lazy='dynamic')
    )

    revisions = db.relationship("Revision", backref="parent_installable")

    def __repr__(self):
        return '<Installable %s:%s>' % (self.id, self.name)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(), nullable=False)


class Revision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(12), nullable=False)
    commit_message = db.Column(db.String(), nullable=False)
    public = db.Column(db.Boolean, default=True, nullable=False)
    uploaded = db.Column(db.DateTime, nullable=False)
    # Link back to our parent installable
    installable = db.Column(db.Integer, db.ForeignKey('installable.id'))
    tar_gz_sha256 = db.Column(db.String(64), nullable=False)
    # No need to store in an API accessible manner, just on disk.
    # Maybe should have a toolshed GPG key and sign all packages with that.
    tar_gz_sig_available = db.Column(db.Boolean, default=False, nullable=False)

    # If a user has this version of this package installed, what should they
    # upgrade to. Need to provide a (probably expensive) method to calculate a
    # full upgrade path?
    replacement_revision = db.Column(db.Integer, db.ForeignKey('revision.id'))

    # Dependency graph data
    dependencies = db.relationship(
        "Revision",
        secondary=revision_adj,
        primaryjoin=id == revision_adj.c.from_revision_id,
        secondaryjoin=id == revision_adj.c.to_revision_id,
        backref="used_in"
    )

    def __repr__(self):
        return '<Revision %s: %s>' % (self.id, self.version)


class SuiteRevision(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(12), nullable=False)
    commit_message = db.Column(db.String(), nullable=False)
    installable = db.Column(db.Integer, db.ForeignKey('installable.id'))

    contained_revisions = db.relationship(
        'Revision', secondary=suite_rr,
        backref=db.backref('suiterevision', lazy='dynamic')
    )
