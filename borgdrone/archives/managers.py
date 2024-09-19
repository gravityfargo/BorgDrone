from borgdrone.logging import logger as log


class ArchivesManager:
    def __init__(self):
        pass

    def create_archive(self, path: str, encryption: str):
        log.debug("CREATING REPOSITORY")

        br = BorgRunner("RepositoryManager.create_repo")
        result_log = br.run(path=path, encryption=encryption)
        if result_log.status == "FAILURE":
            return result_log

        self.get_repository_info(path=path)
        if not self.repo:
            return logger.error(
                event="Repository.GetInfoFailure",
                message="get_repository_info failed to set self.repo. This should not be possible!",
            )

        self.repo.user_id = current_user.id
        self.repo.commit()

        log.debug("Repository created in borgdrone")

        return result_log

    def get_archives(self, repo_path: str, number_of_archives: int = 0):
        command = [
            "borg",
            "list",
            "--json",
        ]
        if number_of_archives > 0:
            num_archives = [
                "--first",
                number_of_archives,
            ]
            command.extend(num_archives)

        command.extend(
            [
                "--format",
                "'{bcomment}{tam}'",
                repo_path,
            ]
        )

        print(command)
