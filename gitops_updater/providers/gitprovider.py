from abc import ABC, abstractmethod


class GitFile(ABC):

    @abstractmethod
    def content(self) -> str:
        pass


class GitProvider(ABC):

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def get_file(self, path: str) -> GitFile:
        ...

    @abstractmethod
    def create_file(self, path: str, content: str, message: str):
        ...

    @abstractmethod
    def update_file(self, gitfile: GitFile, message: str, content: str):
        ...

    @abstractmethod
    def delete_file(self, gitfile: GitFile, message: str):
        ...