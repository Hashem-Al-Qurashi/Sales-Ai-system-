# Senior Chunking Rules - Framework Preservation System

**Reference Document for Optimal Framework Chunking**  
**Quality Standard**: 100% Framework Integrity  
**Approach**: Senior Engineering - Fix Root Causes

---

## CORE PRINCIPLES

### 1. Atomic Framework Preservation
- **NEVER split business frameworks mid-concept**
- **NEVER separate examples from explanations**
- **NEVER break numbered/bulleted lists**
- **NEVER cut formulas or equations**

### 2. Semantic Boundary Respect
- End chunks at natural concept boundaries
- Preserve complete thoughts and logic flow
- Maintain business context and meaning
- Each chunk must be independently understandable

### 3. Size Optimization
- **Target**: 1500 characters per chunk
- **Maximum**: 2000 characters per chunk  
- **Minimum**: 500 characters per chunk
- **Override**: Keep frameworks atomic even if >2000 chars

---

## CHUNKING DECISION TREE

### Step 1: Framework Size Assessment
```
IF framework < 2000 chars:
  → Create single atomic chunk
  → Mark as "atomic_framework"
  → DO NOT SPLIT under any circumstances

IF framework > 2000 chars:
  → Identify natural concept boundaries
  → Split ONLY at major conceptual divisions
  → Mark sections as "framework_section"
  → Ensure each section is complete concept
```

### Step 2: Boundary Detection
```
GOOD BOUNDARIES (Safe to split):
✅ End of complete concept + paragraph break
✅ Transition between major framework components  
✅ After complete examples with explanations
✅ End of numbered list sequences
✅ After complete formulas/equations

BAD BOUNDARIES (NEVER split):
❌ Mid-sentence or mid-paragraph
❌ Between numbered list items (1., 2., 3.)
❌ Between "For example" and the example
❌ Between problem and solution pairs
❌ Mid-formula or mid-equation
❌ Between cause and effect statements
```

### Step 3: Overlap Creation
```
OVERLAP RULES:
- 200 character semantic overlap between chunks
- Include transitional sentences for context
- Preserve logical flow between chunks
- Never overlap mid-sentence

OVERLAP CONTENT:
- Last complete sentence of previous chunk
- Key transitional phrases
- Important context for next section
- Framework component names/headers
```

---

## CONTENT TYPE HANDLING

### Business Frameworks (ATOMIC - Never Split)
```
- Value Equation formulas
- Offer Stack components  
- Complete process workflows
- Business model explanations
- Strategy frameworks with interdependent parts
```

### Lists and Sequences (Preserve Complete)
```
- Numbered lists (1., 2., 3., ...)
- Bulleted lists (•, -, *)
- Step-by-step processes (Step 1, Step 2...)
- Sequential instructions (First, Second, Then...)
```

### Examples and Explanations (Keep Together)
```
- "For example" + the example
- Case studies + their lessons
- Problems + their solutions
- Concepts + their definitions
```

### Formulas and Equations (Never Break)
```
- Mathematical formulas
- Business calculations
- Ratio expressions
- Value equations
```

---

## QUALITY VALIDATION CHECKLIST

### Before Finalizing Chunks:
- [ ] No mid-sentence cuts
- [ ] No split numbered lists
- [ ] No separated examples from concepts
- [ ] No broken formulas/equations
- [ ] Each chunk makes sense alone
- [ ] Semantic overlap preserves flow
- [ ] Framework integrity maintained 100%
- [ ] Business logic preserved completely

### Chunk Independence Test:
```
Ask for each chunk:
1. Can someone understand this without other chunks?
2. Are all referenced examples/lists complete?
3. Is the business logic intact?
4. Would this be useful for retrieval alone?
```

---

## ERROR PATTERNS TO AVOID

### ❌ The "Page Break" Error
```
WRONG: Splitting because text is long
RIGHT: Splitting at conceptual boundaries only
```

### ❌ The "List Fragmentation" Error  
```
WRONG: 
Chunk 1: "1. First point 2. Second"
Chunk 2: "point 3. Third point"

RIGHT:
Chunk 1: "1. First point 2. Second point 3. Third point"
```

### ❌ The "Example Separation" Error
```
WRONG:
Chunk 1: "For example, consider this scenario:"
Chunk 2: "A business owner wants to increase sales..."

RIGHT: Keep "For example" with complete example
```

### ❌ The "Formula Breaking" Error
```
WRONG: Splitting "Value = (Dream Outcome × Likelihood)" 
RIGHT: Keep complete formula together
```

---

## CHUNK OUTPUT FORMAT

### Required Fields for Each Chunk:
```json
{
  "chunk_id": "descriptive_name_01",
  "text": "[Complete chunk text - no truncation]",
  "char_count": 1234,
  "word_count": 234,
  "chunk_type": "atomic_framework|framework_section|supporting",
  "framework_name": "value_equation",
  "preserves_complete_concept": true,
  "overlap_with_previous": "[overlap text if applicable]",
  "contains_formula": true/false,
  "contains_list": true/false,
  "contains_example": true/false,
  "business_logic_intact": true,
  "validation_passed": true
}
```

---

## SIZE GUIDELINES

### Optimal Ranges:
- **Frameworks**: Any size needed for completeness
- **Supporting content**: 1200-1800 characters
- **Examples**: Keep complete regardless of size
- **Lists**: Keep complete regardless of size

### Size Override Rules:
```
IF content type = "atomic_framework":
  → Size limits DO NOT apply
  → Preserve complete framework

IF content type = "supporting":
  → Apply size limits
  → But respect semantic boundaries
```

---

## CONTEXT PRESERVATION

### Maintain These Relationships:
- Cause → Effect chains
- Problem → Solution pairs  
- Setup → Explanation flows
- Framework components → Their descriptions
- Examples → Their lessons/takeaways

### Overlap Strategy:
```
Previous chunk ending: "...this completes the value equation framework."
Overlap in next chunk: "The value equation framework consists of four components. Now let's examine..."
Next chunk start: "The value equation framework consists of four components. Now let's examine the offer stack framework..."
```

---

## REFERENCE DURING CHUNKING

**Before Every Split Decision:**
1. Check this document's boundary rules
2. Verify framework integrity preserved  
3. Confirm semantic completeness
4. Validate overlap quality
5. Test chunk independence

**When In Doubt:**
- Keep content together rather than split
- Preserve business logic over size limits
- Choose quality over arbitrary boundaries
- Maintain framework integrity above all

---

**Remember**: We're building a RAG system for business frameworks. Every chunk must preserve the business value and logic that makes Hormozi's frameworks effective.