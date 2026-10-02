FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY projects/nba-trade-machine/api ./
RUN dotnet publish -c Release -o /published
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /published ./
ENV ASPNETCORE_URLS=http://0.0.0.0:5080
EXPOSE 5080
ENTRYPOINT ["dotnet","TradeApi.dll"]
