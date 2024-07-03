FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:8.0-alpine AS build
ARG TARGETARCH
WORKDIR /app

RUN apk update && apk add --no-cache opus libsodium

COPY . .
RUN dotnet publish -a $TARGETARCH --property:PublishDir=/publish AtcBot.sln

# Final stage
FROM mcr.microsoft.com/dotnet/runtime:8.0-alpine
WORKDIR /app

RUN apk update && apk add --no-cache ffmpeg icu-libs

COPY --from=build /usr/lib/libsodium.so.* .
COPY --from=build /usr/lib/libopus.so.* .

RUN find . -name "libsodium.so.*" -exec mv {} ./libsodium.so \; && \
    find . -name "libopus.so.*" -exec mv {} ./libopus.so \;

COPY --from=build /publish .
USER $APP_UID
ENTRYPOINT ["./AtcBot"]