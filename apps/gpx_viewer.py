# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "folium>=0.20.0",
#     "gpxpy>=1.6.2",
#     "marimo>=0.18.3",
# ]
# [tool.marimo.display]
# theme = "dark"
# ///

import marimo

__generated_with = "0.18.3"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    from dataclasses import dataclass, field
    from io import BytesIO
    from itertools import pairwise
    from json import load
    import urllib.request
    import urllib.parse

    from gpxpy import parse
    from gpxpy.geo import haversine_distance
    import folium
    from folium.plugins import MousePosition

    # provide GitHub repo details
    ORG, REPO, BRANCH = "dkapitan", "marimo-playground", "main"
    tree = f"https://api.github.com/repos/{ORG}/{REPO}/git/trees/{BRANCH}?recursive=1"


    ROOT = mo.notebook_location().parent


    @dataclass
    class Trail:
        name: str
        track: list[tuple] = field(default_factory=list)
        centre: float = field(init=False)
        length: float = field(init=False)

        def __post_init__(self):
            if self.track:
                avg_lat = sum(p[0] for p in self.track) / len(self.track)
                avg_lon = sum(p[1] for p in self.track) / len(self.track)
                self.centre = (avg_lat, avg_lon)
                self.length = sum([haversine_distance(p[0][0], p[0][1], p[1][0], p[1][1]) for p in pairwise(self.track)])
            else:
                self.centre = (52.0, 5.0)  # Default fallback (Netherlands approx)


    def clean_url(url):
        """
        Splits a URL, safely encodes the path and query components
        to handle spaces and control characters, and reconstructs it.
        Created by Gemini.
        """
        # 1. Split the URL into components (scheme, netloc, path, query, fragment)
        #    urlsplit is preferred over urlparse as it treats the path more generically
        parts = urllib.parse.urlsplit(url)

        # 2. Encode the path (e.g., replace spaces with %20)
        #    We assume the path does not contain characters that structure the URL
        #    (like '?' or '#'), as those were stripped by urlsplit.
        safe_path = urllib.parse.quote(parts.path)

        # 3. Encode the query string
        #    safe="=&" ensures we don't encode the delimiters that separate parameters
        safe_query = urllib.parse.quote(parts.query, safe="=&")

        # 4. Encode the fragment (anchor)
        safe_fragment = urllib.parse.quote(parts.fragment)

        # 5. Reassemble the components
        cleaned_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, safe_path, safe_query, safe_fragment))

        return cleaned_url


    # https://github.com/pola-rs/polars/blob/405b194a9a9e40e295571451b99bc68f9bbffcaf/py-polars/src/polars/io/_utils.py#L299
    def process_file_url(path: str, encoding: str | None = None) -> BytesIO:
        with urllib.request.urlopen(clean_url(path)) as f:
            if not encoding or encoding in {"utf8", "utf8-lossy"}:
                return BytesIO(f.read())
            else:
                return BytesIO(f.read().decode(encoding).encode("utf8"))


    def list_gpx_files(tree=tree):
        return [item.get("path") for item in load(process_file_url(tree)).get("tree") if item.get("path").endswith(".gpx")]


    # https://github.com/marimo-team/marimo/blob/355103923506a3296d0e0695fb9e874c737da6ae/marimo/_utils/platform.py#L11
    def is_pyodide() -> bool:
        import sys

        return "pyodide" in sys.modules


    def get_gpx_data(file_path=None, name=None, contents=None, upload=False):
        """Parses contents of GPX file and returns name, center_lat, center_lon, and points."""
        if not upload and file_path:
            name = file_path
            if is_pyodide():
                gpx = parse(process_file_url(file_path).read())
            else:
                with open(file_path, "r") as gpx_file:
                    gpx = parse(gpx_file.read())
        if upload:
            name = name
            gpx = parse(contents)

        points = []
        for track in gpx.tracks:
            if track.name:
                name = track.name
            for segment in track.segments:
                for point in segment.points:
                    points.append((point.latitude, point.longitude))

        if not track:
            for route in gpx.routes:
                if route.name:
                    name = route.name
                for point in route.points:
                    points.append((point.latitude, point.longitude))

        return Trail(name, points)


    def map_track(trail: Trail, tiles: str):
        m = folium.Map(location=trail.centre, zoom_start=13, tiles=tiles)

        folium.PolyLine(
            locations=trail.track,
            color="red",
            weight=4,
            opacity=0.8,
            tooltip=trail.name,
        ).add_to(m)
        folium.Marker(
            location=trail.track[0],
            popup="Start",
            icon=folium.Icon(color="green", icon="play"),
        ).add_to(m)
        folium.Marker(
            location=trail.track[-1],
            popup="End",
            icon=folium.Icon(color="red", icon="stop"),
        ).add_to(m)
        m.fit_bounds(m.get_bounds())
        MousePosition().add_to(m)

        return m
    return ROOT, get_gpx_data, is_pyodide, list_gpx_files, map_track, tree


@app.cell(hide_code=True)
def _(mo):
    upload = mo.ui.switch()
    files = mo.ui.file(filetypes=[".gpx"], kind="area", multiple=True)
    tiles = mo.ui.dropdown(
        options=[
            "Cartodb Positron",
            "CartoDB Voyager",
            "OpenStreetMap Mapnik",
            "Stadia Outdoors",
            "Stadia StamenTerrain",
        ],
        value="Stadia Outdoors",
        label="Choose a map style",
    )
    header = mo.md("""
        ## Simple .gpx tracks viewer

        Always wanted to have your little archive of your favourite trail running or gravelbike rides? You can clone [this repo](https://github.com/dkapitan/marimo-playground) to create your on online archive on GitHub.

        If you want to test it, toggle the switch and upload your own files to play around. It should work with `.gpx` files downloaded from Strava, Garmin or Komoot.""")
    return files, header, tiles, upload


@app.cell(hide_code=True)
def _(files, header, mo, upload):
    if not upload.value:
        display = mo.hstack(
            [header, mo.hstack([mo.md("upload your own files").right(), upload])],
            widths=[1, 1],
        )
    else:
        display = mo.hstack(
            [
                header,
                mo.vstack([mo.hstack([mo.md("upload your own files").right(), upload]), files]),
            ],
            widths=[1, 1],
        )
    display
    return


@app.cell(hide_code=True)
def _(
    ROOT,
    files,
    get_gpx_data,
    is_pyodide,
    list_gpx_files,
    map_track,
    mo,
    tiles,
    tree,
    upload,
):
    trails = []

    if not upload.value:
        if is_pyodide():
            gpx_files = [ROOT / path for path in list_gpx_files(tree)]
        else:
            gpx_files = ROOT.glob("apps/public/gpx-trails/*.gpx")
        for file in gpx_files:
            trail = get_gpx_data(file_path=file, upload=upload.value)
            meta = mo.vstack(
                [
                    mo.md(trail.name),
                    mo.stat(
                        label="trail length",
                        value=str(round(trail.length / 1_000, 1)) + " km",
                    ),
                ]
            )
            trails.append(mo.hstack([meta, map_track(trail, tiles=tiles.value)], widths=[1, 6]))

    if upload.value:
        for file in files.value:
            trail = get_gpx_data(name=file.name, contents=file.contents, upload=upload.value)
            meta = mo.vstack(
                [
                    mo.md(trail.name),
                    mo.stat(
                        label="trail length",
                        value=str(round(trail.length / 1_000, 1)) + " km",
                    ),
                ]
            )
            trails.append(mo.hstack([meta, map_track(trail, tiles=tiles.value)], widths=[1, 6]))

    mo.vstack([mo.right(tiles)] + trails, gap=2)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
