### Installing the package
The server package requires the core package.
To install the server package, first install the core package:
```
$ pip install -e path/to/core/package
$ pip install -e /path/to/server/package
```
### Running tests
Tests are located in the `tests` directory and require `pytest`.
Run them with:
```
$ pytest path/to/test/dir/or/test/file
```