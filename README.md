# glue map
A map viewer for glue (jupyter) using ipyleaflet.

## Testing Commands
Since we cannot easily get error messages from glue-jupyter when a plug-in fails to load, do this:
`python -c 'from glue_map import setup; setup()'` to verify that this plug-in can load.