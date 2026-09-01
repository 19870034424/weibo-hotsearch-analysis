<template>
  <footer class="bg-surface-dark text-on-dark-soft mt-section">
    <div class="max-w-7xl mx-auto px-md py-xxl">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-xl">
        <div class="space-y-md">
          <div class="flex items-center gap-sm">
            <div class="w-8 h-8 flex items-center justify-center">
              <svg viewBox="0 0 24 24" class="w-6 h-6 text-primary">
                <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>
                <path d="M12 2 L12 22 M2 12 L22 12" stroke="currentColor" stroke-width="2"/>
              </svg>
            </div>
            <span class="font-display text-title-md text-on-dark">
              热搜分析
            </span>
          </div>
          <p class="text-body-sm">
            专业的微博热搜数据分析平台，为您提供实时监测、情感分析、趋势预测等功能。
          </p>
        </div>

        <div>
          <h4 class="text-title-sm font-medium text-on-dark mb-md">产品功能</h4>
          <ul class="space-y-sm">
            <li><a href="/" class="text-body-sm hover:text-on-dark transition-colors">实时热搜</a></li>
            <li><a href="/sentiment" class="text-body-sm hover:text-on-dark transition-colors">情感分析</a></li>
            <li><a href="/wordcloud" class="text-body-sm hover:text-on-dark transition-colors">词频分析</a></li>
            <li><a href="/clustering" class="text-body-sm hover:text-on-dark transition-colors">聚类分析</a></li>
          </ul>
        </div>

        <div>
          <h4 class="text-title-sm font-medium text-on-dark mb-md">关于我们</h4>
          <ul class="space-y-sm">
            <li><a href="#" class="text-body-sm hover:text-on-dark transition-colors">公司简介</a></li>
            <li><a href="#" class="text-body-sm hover:text-on-dark transition-colors">联系我们</a></li>
            <li><a href="#" class="text-body-sm hover:text-on-dark transition-colors">加入我们</a></li>
            <li><a href="#" class="text-body-sm hover:text-on-dark transition-colors">帮助中心</a></li>
          </ul>
        </div>

        <div>
          <h4 class="text-title-sm font-medium text-on-dark mb-md">法律条款</h4>
          <ul class="space-y-sm">
            <li><a href="#" class="text-body-sm hover:text-on-dark transition-colors">隐私政策</a></li>
            <li><a href="#" class="text-body-sm hover:text-on-dark transition-colors">服务条款</a></li>
            <li><a href="#" class="text-body-sm hover:text-on-dark transition-colors">数据安全</a></li>
          </ul>
        </div>
      </div>

      <div class="border-t border-surface-dark-elevated mt-xl pt-xl flex flex-col md:flex-row justify-between items-center gap-md">
        <p class="text-body-sm text-on-dark-soft">
          © 2026 微博热搜数据分析系统. All rights reserved.
        </p>
        <div class="flex items-center gap-lg">
          <a href="#" class="text-body-sm hover:text-on-dark transition-colors">隐私政策</a>
          <a href="#" class="text-body-sm hover:text-on-dark transition-colors">服务条款</a>
        </div>
      </div>
    </div>
  </footer>
</template>
