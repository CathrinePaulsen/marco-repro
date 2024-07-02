import os
import pathlib

from flask import Flask, jsonify, send_from_directory, render_template, request

from server import load_compatibility_store, find_compatible_versions

MAVEN_REPOSITORY = pathlib.Path(__file__).parent.parent.resolve() / "resources" / "maven_repository"
LISTING_TEMPLATE = pathlib.Path(__file__).parent.resolve() / "templates" / "directory_listing.html"

app = Flask(__name__, template_folder='templates')


def lookup(gav: str):
    store = load_compatibility_store()
    return store.get(gav, [])


@app.route("/")
def hello_world():
    return jsonify({'message': 'Hello, World!'})


@app.route('/compatibilities/<gav>', methods=['GET'])
def compatibilities(gav: str):
    compatible_versions = lookup(gav)
    # if not compatible_versions:
    #     g, a, v = gav.split(":")
    #     find_compatible_versions(g, a, v, max_num=5, silent=True)
    #     compatible_versions = lookup(gav)
    if compatible_versions:
        return jsonify({'compatible_versions': compatible_versions})
    else:
        return jsonify({'compatible_versions': None})


@app.route('/maven/', defaults={'filename': ""}, methods=['GET'])
@app.route('/maven/<path:filename>', methods=['GET'])
def maven_repository(filename):
    path = pathlib.Path.joinpath(MAVEN_REPOSITORY, filename)

    if pathlib.Path.is_file(path):
        # If the requested path is a file, serve it
        return send_from_directory(MAVEN_REPOSITORY, filename)

    elif pathlib.Path.is_dir(path):
        # If the requested path is a directory, list its content
        directory_content = []
        for item in os.listdir(path):
            if item.startswith("."):
                continue
            item_path = os.path.join(filename, item)
            item_url = f'/maven/{item_path}'
            directory_content.append({'name': item, 'url': item_url})
        return render_template("directory_listing.html", directory_content=directory_content)

    else:
        # Return a 404 response for non-existent paths
        return "Not Found", 404


@app.route('/maven/<path:filename>', methods=['PUT'])
def populate_repository(filename):
    path = pathlib.Path.joinpath(MAVEN_REPOSITORY, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Save the incoming content to the specified file
    with open(path, 'wb') as file:
        file.write(request.data)

    return 'Artifact uploaded successfully', 201


if __name__ == '__main__':
    app.run(debug=True)
