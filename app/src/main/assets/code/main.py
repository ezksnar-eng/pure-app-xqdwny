import os
import time
import sys
import json
from datetime import datetime
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
---------------------------------------------------------
1. إعدادات المفاتيح والنموذج (API Configuration)
---------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
استخدام نموذج ذكي جداً للبرمجة والمراجعة
llm = ChatOpenAI(
model="gpt-4o",
temperature=0.1,
api_key=OPENAI_API_KEY
)
---------------------------------------------------------
2. إنشاء فريق الوكلاء الأوتوماتيكي (Agents System)
---------------------------------------------------------
def create_software_team():
architect = Agent(
role="Mobile Application Architect",
goal="Design fully functional React Native/Expo app architectures with automated GitHub Actions for APK builds.",
backstory="You are a veteran software architect. You create complete, production-ready React Native app structures "
"and ensure that CI/CD pipelines (GitHub Actions) are configured to automatically compile Android APKs.",
verbose=True,
allow_delegation=True,
llm=llm
)
developer = Agent(
role="Lead Mobile & Full-Stack Developer",
goal="Write 100% working, self-contained React Native (Expo) code and backend logic.",
backstory="You write clear, bug-free Expo/React Native UI components and logic. "
"You never leave placeholders like '// TODO' and write full implementations.",
verbose=True,
allow_delegation=False,
llm=llm
)
devops_engineer = Agent(
role="DevOps & GitHub Actions Specialist",
goal="Generate complete GitHub Workflow YAML files to trigger automatic APK build via EAS or Expo CLI.",
backstory="You specialize in continuous integration. You write ready-to-use GitHub Actions workflow files "
"so users can just push code to GitHub and download the resulting APK artifact without hassle.",
verbose=True,
allow_delegation=False,
llm=llm
)
qa_debugger = Agent(
role="Automated QA & Trouble Shooter",
goal="Detect code bugs, optimize state management, and fix runtime errors provided by the user.",
backstory="You excel at diagnosing build logs, React Native errors, and Expo crashes. "
"You immediately refactor code to eliminate all exceptions.",
verbose=True,
allow_delegation=False,
llm=llm
)
return architect, developer, devops_engineer, qa_debugger
---------------------------------------------------------
3. محرك النظام والتأتمتة (Autonomous Engine)
---------------------------------------------------------
class AutonomousAppBuilder:
def init(self, output_dir: str = "./generated_app"):
self.output_dir = output_dir
if not os.path.exists(self.output_dir):
os.makedirs(self.output_dir)
def generate_github_workflow(self):
"""توليد ملف GitHub Actions لبناء الـ APK أوتوماتيكياً عند الرفع على GitHub"""
workflow_dir = os.path.join(self.output_dir, ".github", "workflows")
os.makedirs(workflow_dir, exist_ok=True)
workflow_content = """name: Build Android APK
on:
push:
branches:
- main
- master
jobs:
build:
runs-on: ubuntu-latest
steps:
- name: Checkout repository
uses: actions/checkout@v3
- name: Setup Node.js
uses: actions/setup-node@v3
with:
node-version: 18
cache: 'npm'
- name: Setup Java JDK
uses: actions/setup-java@v3
with:
distribution: 'temurin'
java-version: '17'
- name: Install Dependencies
run: npm install
- name: Install Expo CLI & EAS CLI
run: npm install -g expo-cli eas-cli
- name: Build Android Preview APK
run: npx eas-cli build --platform android --profile preview --non-interactive || npx expo run:android --variant release
env:
EXPO_TOKEN: ${{ secrets.EXPO_TOKEN }}
- name: Upload APK Artifact
uses: actions/upload-artifact@v3
with:
name: app-release.apk
path: android/app/build/outputs/apk/release/*.apk
"""
with open(os.path.join(workflow_dir, "build_apk.yml"), "w", encoding="utf-8") as f:
f.write(workflow_content)
print("✅ تم إنشاء ملف GitHub Action الخاص ببناء الـ APK تلقائياً بنجاح!")
def start_building_loop(self, prompt: str, duration_minutes: int):
"""بدء عملية التطوير المتواصل حسب المدة الزمنية المحددة"""
architect, developer, devops, qa = create_software_team()
duration_seconds = duration_minutes * 60
start_time = time.time()
end_time = start_time + duration_seconds
iteration = 1
current_context = f"App Goal: {prompt}"
print(f"\n🚀 [بدء النظام] جاري إطلاق فريق الذكاء الاصطناعي للعمل المتواصل لمدة {duration_minutes} دقيقة...")
# إنشاء ملفات الـ CI/CD أولاً
self.generate_github_workflow()
while time.time() < end_time:
remaining = int(end_time - time.time())
print(f"\n⏱️ [دورة التطوير #{iteration}] الوقت المتبقي: {remaining // 60}m {remaining % 60}s")
# 1. تصميم الهيكلية المتقدمة
task_arch = Task(
description=f"Design mobile application components and logic for: {current_context}",
expected_output="Complete architecture specification with screen breakdowns and state logic.",
agent=architect
)
# 2. البرمجة الكاملة
task_dev = Task(
description="Write complete App.js, package.json, and component files for React Native / Expo application.",
expected_output="Full React Native source code ready to be pasted into files.",
agent=developer
)
# 3. التدقيق وتأكيد البناء
task_qa = Task(
description="Review the code for any missing imports, undefined variables, or Expo syntax bugs.",
expected_output="Fully tested code with zero bugs.",
agent=qa
)
crew = Crew(
agents=[architect, developer, devops, qa],
tasks=[task_arch, task_dev, task_qa],
process=Process.sequential,
verbose=True
)
result = crew.kickoff()
# حفظ المخرجات
out_file = os.path.join(self.output_dir, f"code_iteration_{iteration}.js")
with open(out_file, "w", encoding="utf-8") as f:
f.write(str(result))
current_context = f"Iterative Refinement #{iteration}. Extend app capabilities, improve UI styling, and add features based on previous code: {result}"
iteration += 1
if time.time() >= end_time:
break
print("\n🎉 [انتهى العمل] اكتمل المشروع! المخرجات جاهزة الآن في مجلد المشروع.")
print(f"📁 مسار المجلد: {os.path.abspath(self.output_dir)}")
print("💡 لتوليد الـ APK تلقائياً: ارفع هذا المجلد إلى حسابك في GitHub وسيقوم GitHub Action ببناء الـ APK وإعطائك رابط التحميل مباشرة!")
def solve_error(self, error_logs: str):
"""نظام الاستجابة وحل المشاكل تلقائياً بدون تعب المستخدم"""
architect, developer, devops, qa = create_software_team()
print("\n🔍 [محلل الأخطاء] جاري قراءة تفاصيل المشكلة وتكليف الوكلاء بإصلاحها...")
fix_task = Task(
description=f"Analyze this error log/issue and fix the source code completely:\n\n{error_logs}",
expected_output="Detailed root-cause analysis and fixed full code ready for execution.",
agent=qa
)
crew = Crew(agents=[qa, developer], tasks=[fix_task], verbose=True)
fixed_result = crew.kickoff()
fix_file = os.path.join(self.output_dir, "FIXED_SOLUTION.js")
with open(fix_file, "w", encoding="utf-8") as f:
f.write(str(fixed_result))
print(f"\n✅ تم حل المشكلة وتعديل الكود تلقائياً! تجد الحل في الملف: {os.path.abspath(fix_file)}")
---------------------------------------------------------
4. القائمة الرئيسية للبرنامج (CLI Interface)
---------------------------------------------------------
if name == "main":
builder = AutonomousAppBuilder()
print("="*60)
print("🤖 نظام بناء التطبيقات الذكي المتكامل (الجيل الجديد)")
print("="*60)
print("1. بناء تطبيق جديد واختياري وضع العمل المستمر (Auto-App Builder)")
print("2. حل وتصلحي مشكلة / خطأ تلقائياً (Auto-Error Solver)")
print("="*60)
choice = input("اختر الخيار (1 أو 2): ").strip()
if choice == "1":
app_idea = input("\n📝 أكتب فكرة التطبيق بالتفصيل:\n> ")
try:
minutes = int(input("\n⏱️ كم دقيقة تريد للوكلاء أن يعملوا باستمرار؟ (مثلاً: 30 أو 60):\n> "))
except ValueError:
minutes = 30
builder.start_building_loop(app_idea, minutes)
elif choice == "2":
print("\n📋 الصق نص الخطأ / المشكلة التي واجهتك (اضغط Enter بعد الانتهاء):")
error_log = sys.stdin.read()
builder.solve_error(error_log)
else:
print("اختيار غير صحيح، يرجى تشغيل الملف مجدداً.")