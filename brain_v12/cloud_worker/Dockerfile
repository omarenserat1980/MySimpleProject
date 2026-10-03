FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY brain_v12/cloud_worker/BrainCloudWorker.csproj brain_v12/cloud_worker/
RUN dotnet restore brain_v12/cloud_worker/BrainCloudWorker.csproj
COPY brain_v12/cloud_worker/ brain_v12/cloud_worker/
RUN dotnet publish brain_v12/cloud_worker/BrainCloudWorker.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /app/publish .
ENV ASPNETCORE_URLS=http://0.0.0.0:8080
ENV BRAIN_CLOUD_API_KEY=
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD wget -qO- http://127.0.0.1:8080/health || exit 1
ENTRYPOINT ["dotnet","BrainCloudWorker.dll"]
