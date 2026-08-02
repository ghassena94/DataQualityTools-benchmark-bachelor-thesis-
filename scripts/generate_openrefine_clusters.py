####################################################
# Benchmark: generate OpenRefine cluster files
# Date: July 2026
####################################################

"""
Generates the cluster files consumed by the ``openrefine`` detector
(``rein/detectors.py``) and the ``openrefine`` repair method (``rein/cleaners.py``).

Both methods replay a clustering result instead of computing one, so they need
``<dataset>/clusters/*.json`` to exist. In the original benchmark those files were
produced by hand in the OpenRefine desktop GUI (Cluster & edit -> method "key
collision", keying function "fingerprint" -> Export clusters) and were never
committed, which is why the methods crash with FileNotFoundError on a fresh clone.

This script drives a real OpenRefine instance over its HTTP API and performs exactly
the same steps for every column of every dataset, writing files in OpenRefine's own
cluster-export format.

Usage:
    # 1. start OpenRefine (any 3.x release) and leave it running
    ./refine -i 127.0.0.1 -p 3333

    # 2. generate the clusters
    python scripts/generate_openrefine_clusters.py
    python scripts/generate_openrefine_clusters.py --datasets beers,adult

Only the standard library is used, so the script runs with the plain host
interpreter as well as inside the benchmark container.
"""

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

# OpenRefine's own defaults for "Cluster & edit", see
# main/webapp/modules/core/scripts/dialogs/clustering-dialog.js
CLUSTER_METHOD = "binning"
KEYING_FUNCTION = "fingerprint"
KEYING_PARAMS = {}

# an empty engine, i.e. no facets applied: all rows take part in the clustering
ENGINE = {"facets": [], "mode": "row-based"}

# the importer options mirror how the benchmark reads its datasets
# (pandas.read_csv with dtype=str), so that the clustered values are byte-identical
# to the cell values the detector later compares against
IMPORT_OPTIONS = {
    "encoding": "UTF-8",
    "separator": ",",
    "ignoreLines": -1,
    "headerLines": 1,
    "skipDataLines": 0,
    "limit": -1,
    "storeBlankRows": True,
    "storeBlankCellsAsNulls": True,
    "guessCellValueTypes": False,
    "processQuotes": True,
    "quoteCharacter": '"',
    "trimStrings": False,
    "includeFileSources": False,
    "includeArchiveFileName": False,
}


class OpenRefineError(RuntimeError):
    pass


class OpenRefineClient:
    """A minimal client for the handful of OpenRefine commands needed here."""

    def __init__(self, base_url, timeout=1800):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, command, params=None):
        url = "{}/command/core/{}".format(self.base_url, command)
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return url

    def _open(self, request):
        try:
            return urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as error:
            raise OpenRefineError(
                "{} {} for {}: {}".format(
                    error.code, error.reason, request.full_url,
                    error.read().decode("utf-8", "replace")[:500],
                )
            )
        except urllib.error.URLError as error:
            raise OpenRefineError(
                "cannot reach OpenRefine at {} ({}). Start it with "
                "'./refine -i 127.0.0.1 -p 3333'.".format(self.base_url, error.reason)
            )

    def _csrf_token(self):
        with self._open(urllib.request.Request(self._url("get-csrf-token"))) as response:
            return json.load(response)["token"]

    def get(self, command, params=None):
        with self._open(urllib.request.Request(self._url(command, params))) as response:
            return json.load(response)

    def post(self, command, params=None, fields=None):
        """POSTs a urlencoded form, adding the CSRF token OpenRefine >= 3.3 requires.

        The token goes into the query string: OpenRefine cannot read it from the body
        of a multipart request, and passing it the same way everywhere keeps the two
        POST helpers consistent.
        """
        query = dict(params or {}, csrf_token=self._csrf_token())
        request = urllib.request.Request(
            self._url(command, query),
            data=urllib.parse.urlencode(fields or {}).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        )
        with self._open(request) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body.strip() else None

    def check_alive(self):
        try:
            version = self.get("get-version")
        except OpenRefineError:
            raise
        return version.get("full_version") or version.get("version") or "unknown"

    def create_project(self, csv_path, project_name):
        """Uploads a CSV and returns the id of the created project."""
        options = dict(IMPORT_OPTIONS, projectName=project_name)
        with open(csv_path, "rb") as handle:
            content = handle.read()

        boundary = "----REIN" + uuid.uuid4().hex
        body = bytearray()
        for name, value in (
            ("project-name", project_name),
            ("format", "text/line-based/*sv"),
            ("options", json.dumps(options)),
        ):
            body += "--{}\r\n".format(boundary).encode()
            body += 'Content-Disposition: form-data; name="{}"\r\n\r\n'.format(name).encode()
            body += value.encode("utf-8") + b"\r\n"
        body += "--{}\r\n".format(boundary).encode()
        body += (
            'Content-Disposition: form-data; name="project-file"; filename="{}"\r\n'
            "Content-Type: text/csv\r\n\r\n".format(os.path.basename(csv_path))
        ).encode()
        body += content + b"\r\n"
        body += "--{}--\r\n".format(boundary).encode()

        request = urllib.request.Request(
            self._url("create-project-from-upload", {"csrf_token": self._csrf_token()}),
            data=bytes(body),
            headers={
                "Content-Type": "multipart/form-data; boundary={}".format(boundary),
                "Content-Length": str(len(body)),
            },
        )
        # OpenRefine answers with a redirect to /project?project=<id> once the import
        # has finished; urllib follows it, so the project id is in the final URL
        with self._open(request) as response:
            final_url = response.geturl()
        project_id = urllib.parse.parse_qs(
            urllib.parse.urlparse(final_url).query
        ).get("project", [None])[0]
        if not project_id:
            raise OpenRefineError(
                "upload of {} did not yield a project id (landed on {})".format(
                    csv_path, final_url
                )
            )
        return project_id

    def column_names(self, project_id):
        models = self.get("get-models", {"project": project_id})
        return [column["name"] for column in models["columnModel"]["columns"]]

    def compute_clusters(self, project_id, column_name):
        """Returns OpenRefine's raw clustering result: a list of lists of {v, c}."""
        return self.post(
            "compute-clusters",
            params={"project": project_id},
            fields={
                "engine": json.dumps(ENGINE),
                "clusterer": json.dumps(
                    {
                        "type": CLUSTER_METHOD,
                        "function": KEYING_FUNCTION,
                        "column": column_name,
                        "params": KEYING_PARAMS,
                    }
                ),
            },
        )

    def delete_project(self, project_id):
        self.post("delete-project", fields={"project": project_id})


def build_export(raw_clusters, project_name, column_name):
    """Rebuilds the object OpenRefine's "Export clusters" button writes to disk.

    The GUI derives the per-cluster fields in ClusteringDialog._updateData: the
    proposed value is the first choice returned by the server (the most frequent
    variant), which is what the repair method writes back into the cells.
    """
    clusters = []
    for choices in raw_clusters:
        lengths = [len(choice["v"]) for choice in choices]
        average = sum(lengths) / len(lengths)
        variance = (sum(length * length for length in lengths) / len(lengths) - average ** 2) ** 0.5
        clusters.append(
            {
                "edit": False,
                "choices": choices,
                "value": choices[0]["v"],
                "size": len(choices),
                "rowCount": sum(choice["c"] for choice in choices),
                "avg": average,
                "variance": variance,
            }
        )

    return {
        "projectName": project_name,
        "columnName": column_name,
        "timeStamp": datetime.now(timezone.utc).isoformat(),
        "clusterMethod": CLUSTER_METHOD,
        "keyingFunction": KEYING_FUNCTION,
        "clusters": clusters,
    }


def safe_filename(column_name):
    keep = [character if character.isalnum() or character in "-_" else "_" for character in column_name]
    return "".join(keep) or "column"


def csv_header(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle), [])


def process_dataset(client, dataset_name, dataset_dir, keep_project=False):
    csv_path = os.path.join(dataset_dir, "dirty.csv")
    if not os.path.isfile(csv_path):
        print("  skipped: no dirty.csv")
        return 0

    header = csv_header(csv_path)
    project_id = client.create_project(csv_path, dataset_name)
    print("  imported as project {}".format(project_id))

    try:
        exports = {}
        for column_name in client.column_names(project_id):
            if column_name not in header:
                # OpenRefine renames duplicate headers, pandas does not; the detector
                # silently ignores such columns, so warn instead of writing dead files
                print("  ! column {!r} has no counterpart in dirty.csv, skipped".format(column_name))
                continue
            raw_clusters = client.compute_clusters(project_id, column_name) or []
            if raw_clusters:
                exports[column_name] = build_export(raw_clusters, dataset_name, column_name)
                print("  {}: {} clusters".format(column_name, len(raw_clusters)))
    finally:
        if not keep_project:
            client.delete_project(project_id)

    clusters_dir = os.path.join(dataset_dir, "clusters")
    if os.path.isdir(clusters_dir):
        # the detector reads every json in the directory, so stale files from an earlier
        # run would silently be mixed into the result
        for stale in sorted(os.listdir(clusters_dir)):
            if stale.endswith(".json"):
                os.remove(os.path.join(clusters_dir, stale))

    if not exports:
        # no directory at all, so the detector reports the method as unavailable rather
        # than silently returning an empty detection dictionary
        print("  no column produced a cluster")
        return 0

    os.makedirs(clusters_dir, exist_ok=True)
    for column_name, export in exports.items():
        path = os.path.join(
            clusters_dir, "clusters_{}_{}.json".format(dataset_name, safe_filename(column_name))
        )
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(export, handle, indent=2, ensure_ascii=False)

    print("  wrote {} file(s) to {}".format(len(exports), clusters_dir))
    return len(exports)


def resolve_datasets_dir(requested):
    if requested:
        return requested
    # on the host the datasets live in rein-datasets/, which docker-compose mounts
    # to the datasets/ path the benchmark hardcodes
    for candidate in ("datasets", "rein-datasets"):
        if os.path.isdir(candidate) and any(
            os.path.isfile(os.path.join(candidate, entry, "dirty.csv"))
            for entry in os.listdir(candidate)
        ):
            return candidate
    return "datasets"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--url", default="http://127.0.0.1:3333", help="base URL of a running OpenRefine"
    )
    parser.add_argument(
        "--datasets-dir",
        default=None,
        help="directory holding the datasets (default: datasets/ or rein-datasets/)",
    )
    parser.add_argument(
        "--datasets", default=None, help="comma-separated dataset names (default: all)"
    )
    parser.add_argument(
        "--keep-projects",
        action="store_true",
        help="do not delete the imported OpenRefine projects afterwards",
    )
    args = parser.parse_args()

    datasets_dir = resolve_datasets_dir(args.datasets_dir)
    if not os.path.isdir(datasets_dir):
        sys.exit("datasets directory {} does not exist".format(datasets_dir))

    if args.datasets:
        names = [name.strip() for name in args.datasets.split(",") if name.strip()]
    else:
        names = sorted(
            entry
            for entry in os.listdir(datasets_dir)
            if os.path.isdir(os.path.join(datasets_dir, entry))
        )

    client = OpenRefineClient(args.url)
    try:
        print("OpenRefine {} at {}".format(client.check_alive(), args.url))
    except OpenRefineError as error:
        sys.exit(str(error))
    print("using datasets in {}/\n".format(datasets_dir))

    total = 0
    failed = []
    for name in names:
        print("{}:".format(name))
        try:
            total += process_dataset(
                client, name, os.path.join(datasets_dir, name), args.keep_projects
            )
        except OpenRefineError as error:
            print("  failed: {}".format(error))
            failed.append(name)
        print()

    print("wrote {} cluster file(s)".format(total))
    if failed:
        sys.exit("failed for: {}".format(", ".join(failed)))


if __name__ == "__main__":
    main()
