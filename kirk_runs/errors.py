"""Failures the versioned run routes return to callers."""


class RunsError(Exception):
    def __init__(self, code, http_status, detail=None, view=None):
        super().__init__(code)
        self.code = code
        self.http_status = http_status
        self.detail = detail or {}
        self.view = view

    def public_error(self):
        error = {"code": self.code}
        if self.code == "reference_mismatch":
            for key in ("probed_release_id", "computing_release_id"):
                if key in self.detail:
                    error[key] = self.detail[key]
        elif self.code == "binding_refused" and "field" in self.detail:
            error["field"] = self.detail["field"]
        return error
