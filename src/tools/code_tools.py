"""Code generation and analysis tools with real LLM integration."""

import time
from typing import Any, Dict, List, Optional

from .base import BaseTool, ToolResult, ToolParameter, ToolParameterType


class CodeGenerateTool(BaseTool):
    """Tool for generating code using LLM."""
    
    name = "code_generate"
    description = "Generate code based on requirements and context using Kimi LLM."
    parameters = [
        ToolParameter(
            name="description",
            description="Description of what code to generate",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="language",
            description="Programming language",
            type=ToolParameterType.STRING,
            required=True,
            enum=["python", "php", "javascript", "typescript", "java", "go", "rust", "other"],
        ),
        ToolParameter(
            name="context",
            description="Additional context or existing code to consider",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="file_path",
            description="Target file path (for context about the file)",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
    ]
    
    def __init__(self, llm_client=None):
        """Initialize with optional LLM client.
        
        Args:
            llm_client: LLM client for code generation (e.g., KimiClient)
        """
        super().__init__()
        self.llm = llm_client
    
    async def run(
        self,
        description: str,
        language: str,
        context: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> ToolResult:
        """Generate code using Kimi LLM.
        
        Args:
            description: What to generate
            language: Programming language
            context: Additional context
            file_path: Target file path
            
        Returns:
            ToolResult with generated code
        """
        start_time = time.time()
        
        try:
            # If no LLM client available, return informative error
            if self.llm is None:
                return ToolResult.error_result(
                    error="CodeGenerateTool requires an LLM client. "
                          "Initialize with: CodeGenerateTool(KimiClient())",
                    tool_name=self.name
                )
            
            # Build the prompt for code generation
            prompt = self._build_generation_prompt(description, language, context, file_path)
            
            # Call LLM - use dict if Message class not available
            try:
                from ..llm.kimi_client import Message
                messages = [
                    Message(role="system", content=self._get_system_prompt(language)),
                    Message(role="user", content=prompt)
                ]
            except ImportError:
                # Fallback for when httpx is not available
                messages = [
                    {"role": "system", "content": self._get_system_prompt(language)},
                    {"role": "user", "content": prompt}
                ]
            
            response = await self.llm.chat(
                messages=messages,
                temperature=0.2,  # Lower temperature for code generation
                max_tokens=4096
            )
            
            # Extract code from response
            generated_code = self._extract_code(response.content, language)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult.success_result(
                data={
                    "language": language,
                    "description": description,
                    "code": generated_code,
                    "file_path": file_path,
                    "model": response.model,
                    "usage": response.usage,
                },
                execution_time_ms=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Code generation failed: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt for code generation."""
        return f"""You are an expert {language} developer. Your task is to generate high-quality, production-ready code.

RULES:
1. Generate ONLY code, no explanations or markdown outside code blocks
2. Use best practices for {language}
3. Include proper error handling where appropriate
4. Add docstrings/comments for complex logic
5. Follow standard naming conventions
6. The code should be complete and runnable

Output ONLY the code, wrapped in a code block with the language specifier."""

    def _build_generation_prompt(
        self, 
        description: str, 
        language: str, 
        context: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> str:
        """Build the prompt for code generation."""
        prompt_parts = [f"Generate {language} code for the following task:\n\n{description}"]
        
        if file_path:
            prompt_parts.append(f"\n\nTarget file path: {file_path}")
        
        if context:
            prompt_parts.append(f"\n\nAdditional context:\n{context}")
        
        prompt_parts.append(f"\n\nPlease provide the complete {language} code:")
        
        return "\n".join(prompt_parts)
    
    def _extract_code(self, content: str, language: str) -> str:
        """Extract code from LLM response."""
        # Try to extract code from markdown code blocks
        if f"```{language}" in content:
            # Extract from language-specific block
            parts = content.split(f"```{language}")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
                return code.strip()
        
        if "```" in content:
            # Extract from generic code block
            parts = content.split("```")
            if len(parts) >= 3:
                # Find the largest code block
                code_blocks = [parts[i] for i in range(1, len(parts), 2)]
                largest_block = max(code_blocks, key=len)
                # Remove language identifier if present
                lines = largest_block.split('\n')
                if lines and lines[0].strip() in ['python', 'php', 'javascript', 'typescript', 'java', 'go', 'rust']:
                    return '\n'.join(lines[1:]).strip()
                return largest_block.strip()
        
        # No code blocks found, return entire content
        return content.strip()


class CodeAnalyzeTool(BaseTool):
    """Tool for analyzing code structure and quality."""
    
    name = "code_analyze"
    description = "Analyze code for structure, patterns, and potential issues."
    parameters = [
        ToolParameter(
            name="code",
            description="Code to analyze",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="language",
            description="Programming language",
            type=ToolParameterType.STRING,
            required=True,
            enum=["python", "php", "javascript", "typescript", "java", "go", "rust", "other"],
        ),
        ToolParameter(
            name="analysis_type",
            description="Type of analysis to perform",
            type=ToolParameterType.STRING,
            required=False,
            default="general",
            enum=["general", "security", "performance", "style", "complexity"],
        ),
    ]
    
    def __init__(self, llm_client=None):
        """Initialize with optional LLM client for enhanced analysis."""
        super().__init__()
        self.llm = llm_client
    
    async def run(
        self,
        code: str,
        language: str,
        analysis_type: str = "general"
    ) -> ToolResult:
        """Analyze code with optional LLM enhancement.
        
        Args:
            code: Code to analyze
            language: Programming language
            analysis_type: Type of analysis
            
        Returns:
            ToolResult with analysis results
        """
        start_time = time.time()
        
        try:
            # Basic static analysis
            analysis = self._perform_static_analysis(code, language, analysis_type)
            
            # If LLM available, enhance with AI analysis
            if self.llm and analysis_type in ["general", "security", "performance"]:
                ai_analysis = await self._perform_ai_analysis(code, language, analysis_type)
                analysis["ai_insights"] = ai_analysis
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult.success_result(
                data=analysis,
                execution_time_ms=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Code analysis failed: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    def _perform_static_analysis(self, code: str, language: str, analysis_type: str) -> Dict:
        """Perform static code analysis."""
        analysis = {
            "language": language,
            "analysis_type": analysis_type,
            "lines": len(code.split('\n')),
            "characters": len(code),
        }
        
        if language == "python":
            analysis["functions"] = code.count("def ")
            analysis["classes"] = code.count("class ")
            analysis["imports"] = [
                line.strip() for line in code.split('\n')
                if line.strip().startswith(('import ', 'from '))
            ]
            analysis["complexity_score"] = self._estimate_complexity(code)
            
        elif language == "php":
            analysis["functions"] = code.count("function ")
            analysis["classes"] = code.count("class ")
            analysis["namespaces"] = code.count("namespace ")
            
        elif language in ["javascript", "typescript"]:
            analysis["functions"] = code.count("function ") + code.count("=>")
            analysis["classes"] = code.count("class ")
            analysis["arrow_functions"] = code.count("=>")
        
        # Security checks
        if analysis_type == "security":
            analysis["security_issues"] = self._check_security(code, language)
        
        return analysis
    
    async def _perform_ai_analysis(self, code: str, language: str, analysis_type: str) -> Dict:
        """Perform AI-enhanced code analysis."""
        prompt = f"""Analyze the following {language} code for {analysis_type} issues:

```{language}
{code[:3000]}  # Limit code size
```

Provide a concise analysis with:
1. Key findings (max 3)
2. Specific issues found (if any)
3. Recommendations for improvement

Format your response as JSON:
{{
    "summary": "Brief summary",
    "findings": ["finding1", "finding2"],
    "issues": [{{"line": 1, "severity": "high", "description": "Issue"}}],
    "recommendations": ["rec1", "rec2"]
}}"""

        try:
            from ..llm.kimi_client import Message
            messages = [
                Message(role="system", content="You are a code analysis expert. Provide structured analysis in JSON format."),
                Message(role="user", content=prompt)
            ]
        except ImportError:
            messages = [
                {"role": "system", "content": "You are a code analysis expert. Provide structured analysis in JSON format."},
                {"role": "user", "content": prompt}
            ]
        
        try:
            response = await self.llm.chat(messages=messages, temperature=0.3, max_tokens=2000)
            
            # Try to parse JSON from response
            import json
            content = response.content
            
            # Extract JSON from markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except Exception as e:
            return {"error": f"AI analysis failed: {str(e)}", "raw_response": response.content[:500] if 'response' in dir() else None}
    
    def _estimate_complexity(self, code: str) -> str:
        """Estimate code complexity (simple heuristic)."""
        lines = len(code.split('\n'))
        indent_levels = [len(line) - len(line.lstrip()) for line in code.split('\n') if line.strip()]
        max_indent = max(indent_levels) if indent_levels else 0
        
        if max_indent > 24 or lines > 200:
            return "high"
        elif max_indent > 16 or lines > 100:
            return "medium"
        return "low"
    
    def _check_security(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Basic security checks."""
        issues = []
        code_lower = code.lower()
        
        # Common security patterns
        security_patterns = {
            "sql_injection": ["select * from", "insert into", "delete from", "update "],
            "hardcoded_secrets": ["password =", "secret =", "api_key =", "token ="],
            "eval_danger": ["eval(", "exec("],
        }
        
        for issue_type, patterns in security_patterns.items():
            for pattern in patterns:
                if pattern in code_lower:
                    issues.append({
                        "type": issue_type,
                        "pattern": pattern,
                        "severity": "high" if issue_type == "sql_injection" else "medium",
                    })
                    break
        
        return issues


class CodeRefactorTool(BaseTool):
    """Tool for refactoring code with LLM assistance."""
    
    name = "code_refactor"
    description = "Refactor code to improve structure, readability, or performance using AI."
    parameters = [
        ToolParameter(
            name="code",
            description="Code to refactor",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="language",
            description="Programming language",
            type=ToolParameterType.STRING,
            required=True,
            enum=["python", "php", "javascript", "typescript", "java", "go", "rust", "other"],
        ),
        ToolParameter(
            name="refactor_type",
            description="Type of refactoring",
            type=ToolParameterType.STRING,
            required=True,
            enum=["extract_method", "rename", "simplify", "optimize", "format", "modernize"],
        ),
        ToolParameter(
            name="target",
            description="Target element to refactor (e.g., function name, variable)",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
    ]
    
    def __init__(self, llm_client=None):
        """Initialize with optional LLM client."""
        super().__init__()
        self.llm = llm_client
    
    async def run(
        self,
        code: str,
        language: str,
        refactor_type: str,
        target: Optional[str] = None
    ) -> ToolResult:
        """Refactor code using LLM.
        
        Args:
            code: Code to refactor
            language: Programming language
            refactor_type: Type of refactoring
            target: Target element
            
        Returns:
            ToolResult with refactored code
        """
        start_time = time.time()
        
        try:
            if self.llm is None:
                return ToolResult.error_result(
                    error="CodeRefactorTool requires an LLM client for AI-powered refactoring.",
                    tool_name=self.name
                )
            
            # Build refactoring prompt
            prompt = self._build_refactor_prompt(code, language, refactor_type, target)
            
            try:
                from ..llm.kimi_client import Message
                messages = [
                    Message(role="system", content=f"You are an expert {language} refactoring specialist."),
                    Message(role="user", content=prompt)
                ]
            except ImportError:
                messages = [
                    {"role": "system", "content": f"You are an expert {language} refactoring specialist."},
                    {"role": "user", "content": prompt}
                ]
            
            response = await self.llm.chat(messages=messages, temperature=0.2, max_tokens=4096)
            
            # Extract refactored code
            refactored_code = self._extract_code(response.content, language)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult.success_result(
                data={
                    "language": language,
                    "refactor_type": refactor_type,
                    "original_code": code,
                    "refactored_code": refactored_code,
                    "target": target,
                    "changes_made": refactored_code != code,
                },
                execution_time_ms=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Refactoring failed: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    def _build_refactor_prompt(
        self, 
        code: str, 
        language: str, 
        refactor_type: str, 
        target: Optional[str]
    ) -> str:
        """Build the refactoring prompt."""
        refactor_descriptions = {
            "extract_method": "Extract a method/function from existing code",
            "rename": "Rename variables/functions for clarity",
            "simplify": "Simplify complex code while preserving functionality",
            "optimize": "Optimize for better performance",
            "format": "Improve code formatting and style",
            "modernize": "Modernize to use latest language features",
        }
        
        prompt = f"""Refactor the following {language} code.

Refactoring type: {refactor_type} - {refactor_descriptions.get(refactor_type, '')}
"""
        if target:
            prompt += f"Target element: {target}\n"
        
        prompt += f"""
Original code:
```{language}
{code}
```

Provide the refactored code only, wrapped in a {language} code block.
Preserve all functionality. Do not add explanations outside the code block."""
        
        return prompt
    
    def _extract_code(self, content: str, language: str) -> str:
        """Extract code from LLM response."""
        if f"```{language}" in content:
            parts = content.split(f"```{language}")
            if len(parts) > 1:
                return parts[1].split("```")[0].strip()
        
        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 3:
                code_blocks = [parts[i] for i in range(1, len(parts), 2)]
                largest_block = max(code_blocks, key=len)
                lines = largest_block.split('\n')
                if lines and lines[0].strip() in ['python', 'php', 'javascript', 'typescript', 'java', 'go', 'rust']:
                    return '\n'.join(lines[1:]).strip()
                return largest_block.strip()
        
        return content.strip()


class CodeTestTool(BaseTool):
    """Tool for generating and running tests."""
    
    name = "code_test"
    description = "Generate or run tests for code."
    parameters = [
        ToolParameter(
            name="action",
            description="Action to perform",
            type=ToolParameterType.STRING,
            required=True,
            enum=["generate", "run", "coverage"],
        ),
        ToolParameter(
            name="code",
            description="Code to test (for generate action)",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="file_path",
            description="Path to test file or file to test",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="language",
            description="Programming language",
            type=ToolParameterType.STRING,
            required=False,
            default="python",
            enum=["python", "php", "javascript", "typescript", "java", "go", "rust"],
        ),
    ]
    
    def __init__(self, llm_client=None):
        """Initialize with optional LLM client for test generation."""
        super().__init__()
        self.llm = llm_client
    
    async def run(
        self,
        action: str,
        code: Optional[str] = None,
        file_path: Optional[str] = None,
        language: str = "python"
    ) -> ToolResult:
        """Generate or run tests.
        
        Args:
            action: Action type
            code: Code to test
            file_path: File path
            language: Programming language
            
        Returns:
            ToolResult with test results
        """
        start_time = time.time()
        
        try:
            if action == "generate":
                if not code:
                    return ToolResult.error_result(
                        error="Code is required for test generation",
                        tool_name=self.name
                    )
                
                # Use LLM for intelligent test generation if available
                if self.llm:
                    test_code = await self._generate_tests_with_llm(code, language, file_path)
                else:
                    test_code = self._generate_test_template(code, language)
                
                execution_time = (time.time() - start_time) * 1000
                
                return ToolResult.success_result(
                    data={
                        "language": language,
                        "test_code": test_code,
                        "framework": self._get_test_framework(language),
                        "ai_generated": self.llm is not None,
                    },
                    execution_time_ms=execution_time,
                    tool_name=self.name
                )
            
            elif action == "run":
                execution_time = (time.time() - start_time) * 1000
                return ToolResult.success_result(
                    data={
                        "status": "placeholder",
                        "note": "Real test execution would run the test framework",
                    },
                    execution_time_ms=execution_time,
                    tool_name=self.name
                )
            
            elif action == "coverage":
                execution_time = (time.time() - start_time) * 1000
                return ToolResult.success_result(
                    data={
                        "status": "placeholder",
                        "note": "Real coverage analysis would use coverage tools",
                    },
                    execution_time_ms=execution_time,
                    tool_name=self.name
                )
            
            else:
                return ToolResult.error_result(
                    error=f"Unknown action: {action}",
                    tool_name=self.name
                )
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Test operation failed: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    async def _generate_tests_with_llm(self, code: str, language: str, file_path: Optional[str] = None) -> str:
        """Generate tests using LLM."""
        framework = self._get_test_framework(language)
        
        prompt = f"""Generate comprehensive unit tests for the following {language} code.

Code to test:
```{language}
{code[:4000]}  # Limit size
```

Requirements:
1. Use {framework} testing framework
2. Cover normal cases, edge cases, and error cases
3. Use descriptive test names
4. Include setup/teardown if needed
5. Add comments explaining what each test verifies

Output only the test code, wrapped in a {language} code block."""

        try:
            from ..llm.kimi_client import Message
            messages = [
                Message(role="system", content=f"You are a {language} testing expert. Generate high-quality unit tests."),
                Message(role="user", content=prompt)
            ]
        except ImportError:
            messages = [
                {"role": "system", "content": f"You are a {language} testing expert. Generate high-quality unit tests."},
                {"role": "user", "content": prompt}
            ]
        
        response = await self.llm.chat(messages=messages, temperature=0.3, max_tokens=4096)
        
        # Extract code from response
        content = response.content
        if f"```{language}" in content:
            parts = content.split(f"```{language}")
            if len(parts) > 1:
                return parts[1].split("```")[0].strip()
        
        if "```" in content:
            parts = content.split("```")
            if len(parts) >= 3:
                return parts[1].split("```")[0].strip()
        
        return content.strip()
    
    def _get_test_framework(self, language: str) -> str:
        """Get the default test framework for a language."""
        frameworks = {
            "python": "pytest",
            "php": "PHPUnit",
            "javascript": "Jest",
            "typescript": "Jest",
            "java": "JUnit",
            "go": "testing",
            "rust": "built-in test",
        }
        return frameworks.get(language, "unknown")
    
    def _generate_test_template(self, code: str, language: str) -> str:
        """Generate a basic test template (fallback)."""
        if language == "python":
            return '''import pytest
from module import function_to_test

def test_function_to_test():
    """Test function_to_test"""
    # Arrange
    
    # Act
    result = function_to_test()
    
    # Assert
    assert result is not None
'''
        elif language == "php":
            return '''<?php

use PHPUnit\\Framework\\TestCase;

class FunctionTest extends TestCase
{
    public function testFunction(): void
    {
        // Arrange
        
        // Act
        $result = functionToTest();
        
        // Assert
        $this->assertNotNull($result);
    }
}
'''
        else:
            return f"// TODO: Generate test template for {language}\n"


class CodeReviewTool(BaseTool):
    """Tool for performing AI-powered code reviews."""
    
    name = "code_review"
    description = "Perform an AI-powered code review and provide detailed feedback."
    parameters = [
        ToolParameter(
            name="code",
            description="Code to review",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="language",
            description="Programming language",
            type=ToolParameterType.STRING,
            required=True,
            enum=["python", "php", "javascript", "typescript", "java", "go", "rust", "other"],
        ),
        ToolParameter(
            name="focus",
            description="Areas to focus on",
            type=ToolParameterType.ARRAY,
            required=False,
            default=None,
        ),
    ]
    
    def __init__(self, llm_client=None):
        """Initialize with optional LLM client."""
        super().__init__()
        self.llm = llm_client
    
    async def run(
        self,
        code: str,
        language: str,
        focus: Optional[List[str]] = None
    ) -> ToolResult:
        """Perform code review.
        
        Args:
            code: Code to review
            language: Programming language
            focus: Areas to focus on
            
        Returns:
            ToolResult with review comments
        """
        start_time = time.time()
        
        try:
            focus_areas = focus or ["readability", "performance", "security"]
            
            if self.llm is None:
                # Basic placeholder review
                return ToolResult.success_result(
                    data={
                        "language": language,
                        "focus_areas": focus_areas,
                        "lines_reviewed": len(code.split('\n')),
                        "comments": [
                            {
                                "line": None,
                                "type": "info",
                                "message": "Code review requires an LLM client for AI-powered analysis.",
                            }
                        ],
                        "summary": f"Reviewed {len(code.split(chr(10)))} lines of {language} code (basic mode).",
                    },
                    tool_name=self.name
                )
            
            # AI-powered code review
            review = await self._perform_ai_review(code, language, focus_areas)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult.success_result(
                data={
                    "language": language,
                    "focus_areas": focus_areas,
                    "lines_reviewed": len(code.split('\n')),
                    "comments": review.get("comments", []),
                    "summary": review.get("summary", ""),
                    "rating": review.get("rating"),
                    "suggestions": review.get("suggestions", []),
                },
                execution_time_ms=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Code review failed: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    async def _perform_ai_review(self, code: str, language: str, focus_areas: List[str]) -> Dict:
        """Perform AI-powered code review."""
        prompt = f"""Perform a code review of the following {language} code.

Focus areas: {', '.join(focus_areas)}

Code:
```{language}
{code[:4000]}  # Limit size
```

Provide your review in JSON format:
{{
    "summary": "Overall assessment (2-3 sentences)",
    "rating": "excellent|good|fair|needs_improvement",
    "comments": [
        {{
            "line": 10,
            "type": "praise|suggestion|issue|question",
            "message": "Specific feedback"
        }}
    ],
    "suggestions": [
        "Actionable improvement suggestion 1",
        "Actionable improvement suggestion 2"
    ]
}}"""

        try:
            from ..llm.kimi_client import Message
            messages = [
                Message(role="system", content="You are a senior code reviewer. Provide constructive, specific feedback."),
                Message(role="user", content=prompt)
            ]
        except ImportError:
            messages = [
                {"role": "system", "content": "You are a senior code reviewer. Provide constructive, specific feedback."},
                {"role": "user", "content": prompt}
            ]
        
        try:
            response = await self.llm.chat(messages=messages, temperature=0.4, max_tokens=3000)
            
            import json
            content = response.content
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except Exception as e:
            return {
                "summary": f"Review failed: {str(e)}",
                "comments": [],
                "suggestions": []
            }
