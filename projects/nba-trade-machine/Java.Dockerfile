FROM eclipse-temurin:17-jdk AS builder
WORKDIR /repo
COPY shared/java/ ./shared/java/
COPY projects/nba-trade-machine/java/ ./projects/nba-trade-machine/java/
RUN mkdir build && javac -d build shared/java/*.java projects/nba-trade-machine/java/*.java
FROM eclipse-temurin:17-jre
WORKDIR /repo
COPY --from=builder /repo/build ./build
COPY projects/nba-trade-machine/config ./projects/nba-trade-machine/config
COPY projects/nba-trade-machine/data ./projects/nba-trade-machine/data
ENV JAVA_BIND=0.0.0.0
EXPOSE 8081
CMD ["java","-cp","build","TradeServer","serve",".","8081"]
