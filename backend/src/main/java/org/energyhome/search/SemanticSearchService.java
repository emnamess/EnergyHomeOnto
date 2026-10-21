package org.energyhome.search;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionHTTP;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.rdf.model.RDFNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class SemanticSearchService {
    private final LocalQueryInterpreter interpreter;
    private final String queryUrl;

    public SemanticSearchService(LocalQueryInterpreter interpreter,
            @Value("${energyhome.fuseki.query-url}") String queryUrl) {
        this.interpreter = interpreter;
        this.queryUrl = queryUrl;
    }

    public SearchResponse search(String question) {
        var interpreted = interpreter.interpret(question);
        List<Map<String, String>> rows = new ArrayList<>();
        try (QueryExecution execution = QueryExecutionHTTP.service(queryUrl)
                .query(interpreted.sparql())
                .build()) {
            ResultSet results = execution.execSelect();
            while (results.hasNext()) {
                QuerySolution solution = results.nextSolution();
                Map<String, String> row = new LinkedHashMap<>();
                for (String variable : results.getResultVars()) {
                    RDFNode value = solution.get(variable);
                    if (value != null) row.put(variable, value.toString());
                }
                rows.add(row);
            }
        }
        return new SearchResponse(interpreted.interpretation(), interpreted.sparql(), rows);
    }
}
