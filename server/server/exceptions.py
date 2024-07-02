class BaseJarNotFoundException(Exception):
    """Raised when the base jar used to find compatible candidates is not found."""


class CandidateJarNotFoundException(Exception):
    """Raised when a candidate jar used for compatibility comparison with the base jar is not found."""


class PomNotFoundException(Exception):
    """Raised when the pom could not be found."""


class GithubRepoNotFoundException(Exception):
    """Raised when a repo could not be found by the Github API."""


class GithubTagNotFoundException(Exception):
    """Could not find a tag matching the dependency's version."""


class GithubRepoDownloadFailedException(Exception):
    """Raised when a repo could not be downloaded from Github."""


class MavenSurefireTestFailedException(Exception):
    """Raised when mvn surefire:test did not produce surefire-reports, likely due to not running properly."""


class MavenCompileFailedException(Exception):
    """Raised when mvn compile fails."""


class MavenResolutionFailedException(Exception):
    """Maven failed at resolving dependencies."""


class MavenNoPomInDirectoryException(Exception):
    """Raised when mvn returns 'there is no POM in this directory'/'MissingProjectException'"""


class BaseMavenCompileTimeout(Exception):
    """Compilation for creating of base template exceeded timeout threshold."""


class CandidateMavenCompileTimeout(Exception):
    """Compilation for creating of candidate template exceeded timeout threshold."""


class BaseMavenTestTimeout(Exception):
    """Running the tests for the base template exceeded timeout threshold."""


class CandidateMavenTestTimeout(Exception):
    """Running the tests for the candidate template exceeded timeout threshold."""
