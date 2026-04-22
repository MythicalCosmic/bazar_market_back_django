from django.utils import timezone
from base.interfaces.product import IProductRepository
from base.interfaces.product_image import IProductImageRepository
from base.interfaces.category import ICategoryRepository
from base.interfaces.discount import IDiscountRepository
from base.exceptions import NotFoundError