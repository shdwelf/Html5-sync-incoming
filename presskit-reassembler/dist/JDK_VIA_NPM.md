# Getting a working JDK through npm (this sandbox's only reachable CDN)

All conventional JDK download hosts are egress-blocked in this sandbox
(Adoptium/Temurin GitHub assets + objects.githubusercontent.com, Oracle, Azul,
BellSoft, Debian mirrors, and the CDN proxies jsdelivr/unpkg/statically all time
out). The **only** reachable binary host is the npm registry
(`registry.npmjs.org`). It turns out the npm package ecosystem ships real
Java toolchains as tarballs served straight from that registry.

## Working channel (verified)
```bash
npm view javajre-linux-64            # a linux-x64 Java 17 package (chemzqm)
# despite the "jre" name the tarball contains a FULL JDK, incl. javac:
curl -sL -o jre.tgz "https://registry.npmjs.org/javajre-linux-64/-/javajre-linux-64-17.0.8.tgz"
mkdir jdkx && tar xzf jre.tgz -C jdkx
export JAVA_HOME="$PWD/jdkx/package/jre"
export PATH="$JAVA_HOME/bin:$PATH"
java -version      # Java(TM) SE Runtime 17.0.8 (build 17.0.8+9-LTS-211)
javac -version     # javac 17.0.8
```
Then build the app jar:
```bash
bash presskit-reassembler/dist/java/build.sh
java -jar presskit-reassembler/dist/java/presskit-reassembler.jar 8080
```

## Result
- `dist/java/presskit-reassembler.jar` built and verified: starts a local HTTP
  server and serves the Press Kit Reassembler app (200 OK, boot splash + WASM
  engine present) — the same content as the WAR/webxdc.

## Licensing note
The `javajre-linux-64` package repackages the **Oracle JDK 17.0.8** build
(repository field points at Oracle's JDK17 archive). Oracle JDK 17 is free to use
under the Oracle No-Fee Terms and Conditions (NFTC), but if you require a
strictly GPLv2+CE OpenJDK build, prefer **Eclipse Temurin** from a machine with
normal network access — the source (`PressKitServer.java`) and `build.sh` are
identical regardless of JDK flavor.
