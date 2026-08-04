"""The one exception the tool raises on purpose.

Anything a user can cause — a missing script, a recording with no audio, a GPU that
isn't there — is reported as a `RoughCutError` whose message is written to be read by
a person. The CLI prints it and exits; nothing else catches it. Any other exception
escaping to the top level is a bug and is allowed to show its traceback.
"""


class RoughCutError(Exception):
    """A problem the user can act on, phrased for the user."""
