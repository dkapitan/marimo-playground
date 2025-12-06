# /// script
# requires-python = ">=3.12"
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
def _():
    from dataclasses import dataclass, field
    from itertools import pairwise

    from gpxpy import parse
    from gpxpy.geo import haversine_distance
    import folium
    from folium.plugins import MousePosition


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


    def get_gpx_data(name, contents):
        """Parses contents of GPX file and returns name, center_lat, center_lon, and points."""
        # with open(file_path, "r") as gpx_file:
        #     gpx = parse(gpx_file)
        gpx = parse(contents)
    
        name = name
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
    return get_gpx_data, map_track


@app.cell(hide_code=True)
def _(mo):
    HERE = mo.notebook_location()

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
    return files, tiles


@app.cell
def _(files, mo):
    mo.left(files)
    return


@app.cell(hide_code=True)
def _(files, get_gpx_data, map_track, mo, tiles):
    trails = []
    for file in files.value:
        trail = get_gpx_data(file.name, file.contents)
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
