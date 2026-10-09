zip -r ghassets/jmdict-stardict.zip stardict/jmdict -x "*.DS_Store"
zip -r ghassets/jmnedict-stardict.zip stardict/jmnedict -x "*.DS_Store"

gh release create v1.0.0 \
  ghassets/jmdict-stardict.zip \
  ghassets/jmnedict-stardict.zip \
  --title "JMDict & JMNEDict v1.0.0" \
  --notes "Built Aug 13, 2026"