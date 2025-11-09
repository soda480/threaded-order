# threaded
A base class to facilitate multithreading with dependencies

## Development

Clone the repository and ensure the latest version of Docker is installed on your development server.

Build the Docker image:
```sh
docker image build \
-t threaded:latest .
```

Run the Docker container:
```sh
docker container run \
--rm \
-it \
-v $PWD:/code \
threaded:latest \
bash
```

Execute the dev pipeline:
```sh
make dev
```