package com.example.shop.controller;

import org.springframework.web.bind.annotation.*;
import java.util.ArrayList;
import java.util.List;

@RestController
@RequestMapping("/api/search")
@CrossOrigin(origins = "*")
public class SearchController {

    @GetMapping("/suggestions")
    public List<String> getSuggestions(@RequestParam String q) {
        List<String> suggestions = new ArrayList<>();
        // VULNERABILITY: Reflecting input in suggestions (simulating a naive search engine)
        // In a real scenario, this might be "Results for <b>" + q + "</b>"
        // Here we just return the query as part of a suggestion to be rendered with v-html on frontend
        suggestions.add("Laptop similar to " + q);
        suggestions.add("Accessories for " + q);
        suggestions.add("Cheap " + q);
        return suggestions;
    }
}
