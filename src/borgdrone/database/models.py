from borgdrone.extensions import db


class CRUD:
    def __init__(self, model):
        self.model = model

    def _create(self, **kwargs):
        if not kwargs.get("commit_instance", True):
            return self.model()

        instance = self.model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance

    def _get_one(self, filter_name, filter_value):
        instance = self.model.query.filter_by(**{filter_name: filter_value}).first()
        return instance

    def _get_all_by(self, filter_name, filter_value):
        instances = self.model.query.filter_by(**{filter_name: filter_value}).all()
        return instances

    def _get_all(self):
        instances = self.model.query.all()
        return instances

    def _get_last(self):
        instance = self.model.query.order_by(self.model.id.desc()).first()
        return instance

    def _update(self, instance, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        db.session.commit()

    def _delete(self, instance):
        db.session.delete(instance)
        db.session.commit()

    def _delete_all_by(self, filter_name, filter_value):
        instances = self._get_all_by(filter_name, filter_value)
        if not instances:
            return

        for instance in instances:
            db.session.delete(instance)
        db.session.commit()

    def get_by_id(self, id_key: int):
        instance = self._get_one("id", id_key)
        self.archive = instance
        return instance


# @dataclass
# @dataclass
# class Archive(db.Model):
#     __tablename__ = "archive"
#     id = mapped_column(String(64), primary_key=True)
#     user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
#     repo_id = mapped_column(Integer, ForeignKey("repository.id"), nullable=False)
#     bundle_id = mapped_column(Integer, ForeignKey("backupbundle.id"), nullable=True)
#     backup_directory_id = mapped_column(Integer, ForeignKey("backupdirectory.id"), nullable=True)

#     name = mapped_column(String(1000), nullable=False)
#     hostname = mapped_column(String(1000), nullable=False)
#     start = mapped_column(String(1000), nullable=False)
#     time = mapped_column(String(1000), nullable=False)
#     username = mapped_column(String(1000), nullable=False)
