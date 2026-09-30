FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY brain_v12/cloud_worker/BrainCloudWorker.csproj brain_v12/cloud_worker/
RUN dotnet restore brain_v12/cloud_worker/BrainCloudWorker.csproj
COPY brain_v12/cloud_worker/ brain_v12/cloud_worker/
RUN dotnet publish brain_v12/cloud_worker/BrainCloudWorker.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/runtime:10.0
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet","BrainCloudWorker.dll"]
