e ninja

### Find all classes that do not have att. "data.vertical_domain"

{
"query": {
"bool": {
  "must_not": [{"exists":{"field":"data.vertical_domain"}}]
}
},
"aggs":{
  "class":{
"terms":{"field":"class.keyword"}
}
}
}