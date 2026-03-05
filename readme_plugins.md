# Plugin 
## Check if plugin is loaded 
```
SHOW PROCEDURES
YIELD name
WHERE name STARTS WITH 'gds.'
```

## GDS Version
```
RETURN gds.version();
```

# Licence
## Check if files exist in pod 

```
kubectl exec my-neo4j-release-0 -n application -- ls -l /licenses/gds.license
```

## Check if it is readable

```
kubectl exec my-neo4j-release-0 -n application -- stat /licenses/gds.license
```

## Check license state
```
RETURN gds.isLicensed();
CALL gds.license.state();
```