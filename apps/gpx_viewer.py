# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "folium>=0.20.0",
#     "fsspec==2025.12.0",
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
def _():
    from dataclasses import dataclass, field
    from itertools import pairwise

    from gpxpy import parse
    from gpxpy.geo import haversine_distance
    from fsspec.implementations.github import GithubFileSystem
    import folium
    from folium.plugins import MousePosition


    # reading from GitHub repo by default
    ORG, REPO = "dkapitan", "marimo-playground"
    fs = GithubFileSystem(ORG, REPO)


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


    def get_gpx_data(file_path=None, name=None, contents=None, upload=False):
        """Parses contents of GPX file and returns name, center_lat, center_lon, and points."""
        if not upload and file_path:
            with fs.open(file_path, "r") as gpx_file:
                name = file_path
                gpx = parse(gpx_file)

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

        folium.PolyLine(locations=trail.track, color="red", weight=4, opacity=0.8, tooltip=trail.name).add_to(m)
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
    return fs, get_gpx_data, map_track


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
        display = mo.hstack([header, mo.hstack([mo.md("upload your own files").right(), upload])], widths=[1, 1])
    else:
        display = mo.hstack(
            [header, mo.vstack([mo.hstack([mo.md("upload your own files").right(), upload]), files])], widths=[1, 1]
        )
    display
    return


@app.cell(hide_code=True)
def _(files, fs, get_gpx_data, map_track, mo, tiles, upload):
    trails = []

    if not upload.value:
        for file in fs.glob("apps/public/gpx-trails/*.gpx"):
            trail = get_gpx_data(file_path=file, upload=upload.value)
            meta = mo.vstack(
                [mo.md(trail.name), mo.stat(label="trail length", value=str(round(trail.length / 1_000, 1)) + " km")]
            )
            trails.append(mo.hstack([meta, map_track(trail, tiles=tiles.value)], widths=[1, 6]))

    if upload.value:
        for file in files.value:
            trail = get_gpx_data(name=file.name, contents=file.contents, upload=upload.value)
            meta = mo.vstack(
                [mo.md(trail.name), mo.stat(label="trail length", value=str(round(trail.length / 1_000, 1)) + " km")]
            )
            trails.append(mo.hstack([meta, map_track(trail, tiles=tiles.value)], widths=[1, 6]))

    mo.vstack([mo.right(tiles)] + trails, gap=2)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
