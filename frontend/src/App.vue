<!--
  Mirro 根组件 — 应用外壳
  业务角色：提供全局布局框架（导航栏 + 内容区），所有页面在此插槽内渲染。
-->
<script setup lang="ts">
import NavBar from '@/components/NavBar.vue'
</script>

<template>
  <!-- 全局布局：顶部导航 + 主内容区 -->
  <div class="min-h-screen bg-slate-50">
    <NavBar />
    <main class="max-w-4xl mx-auto px-4 py-8">
      <!-- 页面内容通过路由动态渲染 -->
      <router-view />
    </main>

    <!-- 页脚 — 项目标识 -->
    <footer class="text-center py-6 text-sm text-slate-400">
      Mirro AI — 面向年轻人的智能问题解决引擎
    </footer>
  </div>
</template>
