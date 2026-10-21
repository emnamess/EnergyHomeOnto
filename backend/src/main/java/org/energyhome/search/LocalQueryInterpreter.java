package org.energyhome.search;

import java.text.Normalizer;
import java.util.Locale;

import org.springframework.stereotype.Service;

/** Small, deterministic French-to-SPARQL rule engine; no remote AI/API is used. */
@Service
public class LocalQueryInterpreter {
    private static final String NS = "http://www.example.org/energyhomeonto#";

    public InterpretedQuery interpret(String input) {
        if (input == null || input.isBlank()) {
            throw new IllegalArgumentException("Saisissez une question.");
        }
        String normalized = normalize(input);
        String target;
        String label;
        if (normalized.matches(".*\\b(batterie|batteries)\\b.*")) {
            target = "Batterie";
            label = "batterie";
        } else if (normalized.matches(".*\\b(panneau|panneaux|solaire|solaires)\\b.*")) {
            target = "PanneauSolaire";
            label = "panneau solaire";
        } else if (normalized.matches(".*\\b(eolienne|eoliennes)\\b.*")) {
            target = "Eolienne";
            label = "éolienne";
        } else {
            throw new IllegalArgumentException(
                    "Concept non reconnu. Essayez maison, batterie, panneau solaire ou éolienne.");
        }

        boolean autonomous = normalized.contains("autonome") || normalized.contains("autonomes");
        String houseClass = autonomous ? "MaisonAutonome" : "Maison";
        String interpretation = (autonomous ? "Maisons autonomes" : "Maisons")
                + " possédant un(e) " + label;
        String sparql = "PREFIX : <" + NS + ">\n"
                + "SELECT DISTINCT ?maison WHERE {\n"
                + "  ?maison a :" + houseClass + " ;\n"
                + "          :possede ?equipement .\n"
                + "  ?equipement a :" + target + " .\n"
                + "}";
        return new InterpretedQuery(interpretation, sparql);
    }

    private String normalize(String input) {
        return Normalizer.normalize(input.toLowerCase(Locale.FRENCH), Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "")
                .replaceAll("[^\\p{L}\\p{N} ]", " ")
                .replaceAll("\\s+", " ")
                .trim();
    }

    public record InterpretedQuery(String interpretation, String sparql) {
    }
}
