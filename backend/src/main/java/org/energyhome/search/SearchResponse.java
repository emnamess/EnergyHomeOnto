package org.energyhome.search;

import java.util.List;
import java.util.Map;

public record SearchResponse(String interpretation, String sparql, List<Map<String, String>> results) {
}
